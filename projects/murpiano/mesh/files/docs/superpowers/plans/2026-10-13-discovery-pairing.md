# Discovery & Pairing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows (C#/.NET) and Android (Kotlin) apps discover each other on the same LAN via mDNS, pair once through a human-confirmed PIN, and remember each other for future connections over a TLS-secured TCP channel.

**Architecture:** Two independent native apps that share no code, only a protocol (mDNS service type/TXT fields, TLS handshake, PIN derivation algorithm, paired-device record shape) implemented twice. Each app layers Identity → Discovery → Pairing (TLS handshake + PIN + store) → UI.

**Tech Stack:**
- Windows: .NET 8, WPF, `Makaretu.Dns` (mDNS), `System.Net.Security.SslStream`, `System.Security.Cryptography.X509Certificates`, `System.Text.Json`.
- Android: Kotlin, `NsdManager` (mDNS), `javax.net.ssl.SSLContext`/`SSLEngine`, Android Keystore, Room.

**Spec:** `docs/superpowers/specs/2026-10-13-discovery-pairing-design.md`

## Global Constraints

- mDNS service type: `_meshlink._tcp`. TXT records: `id=<device-uuid>`, `name=<device-name>`, `platform=windows|android`.
- PIN derivation algorithm (must match exactly on both platforms):
  1. Take both peers' certificate SHA-256 fingerprints as lowercase hex strings (64 chars, no separators).
  2. Sort the two strings ascending (ordinal/lexicographic string comparison).
  3. Concatenate `sorted[0] + sorted[1]` as UTF-8 bytes.
  4. SHA-256 hash the concatenation.
  5. `num = (hash[0] << 16 | hash[1] << 8 | hash[2]) % 1000000`.
  6. PIN = `num` formatted as 6-digit zero-padded decimal.
- Paired-device record fields: `uuid`, `name`, `fingerprint`, `last_ip`, `paired_at` (ISO-8601 UTC string).
- TLS handshake timeout: 10 seconds, then surface "Connection failed".
- Known device with a changed fingerprint must never be silently trusted — always force re-pair through the PIN flow.

## Review Focus

- Two devices with identical fingerprint byte prefixes but different full fingerprints must still produce different PINs (hash collision on truncation) — pin derivation test covers full-fingerprint sensitivity, not just the two canned vectors.
- Reconnecting to a `uuid` whose stored fingerprint no longer matches the live peer certificate must reject and demand re-pairing, never silently proceed (covered in Task 6 and Task 13 handshake tests).
- mDNS advertise/browse must survive the service already being registered (e.g. app restart while a stale record lingers) without crashing — covered by Task 5 and Task 12 restart tests.
- Paired-device store must tolerate a missing/corrupt file (first run, or JSON corruption) by treating it as empty rather than crashing the app — covered in Task 4 and Task 11.
- PIN confirmation UI must handle the "Not matching" path distinctly from a handshake timeout, both ending in "Pairing failed" but without leaving a half-written paired-device record — covered in Task 7 and Task 14.

---

## Task 1: Scaffold Windows solution structure

**Files:**
- Create: `src/windows/Mesh.sln`
- Create: `src/windows/Mesh.Core/Mesh.Core.csproj`
- Create: `src/windows/Mesh.Core/PinDerivation.cs`
- Create: `src/windows/Mesh.App/Mesh.App.csproj`
- Create: `src/windows/Mesh.App/App.xaml`
- Create: `src/windows/Mesh.App/App.xaml.cs`
- Create: `src/windows/Mesh.Tests/Mesh.Tests.csproj`
- Create: `src/windows/Mesh.Tests/PinDerivationTests.cs`

**Interfaces:**
- Produces: `Mesh.Core.PinDerivation.Derive(string fingerprintA, string fingerprintB) -> string` (6-digit PIN).

- [ ] **Step 1: Create the solution and projects**

```bash
mkdir -p src/windows
cd src/windows
dotnet new sln -n Mesh
dotnet new classlib -n Mesh.Core -o Mesh.Core -f net8.0
dotnet new wpf -n Mesh.App -o Mesh.App -f net8.0
dotnet new xunit -n Mesh.Tests -o Mesh.Tests -f net8.0
dotnet sln add Mesh.Core/Mesh.Core.csproj Mesh.App/Mesh.App.csproj Mesh.Tests/Mesh.Tests.csproj
cd Mesh.Tests && dotnet add reference ../Mesh.Core/Mesh.Core.csproj && cd ..
cd Mesh.App && dotnet add reference ../Mesh.Core/Mesh.Core.csproj && cd ..
```

- [ ] **Step 2: Write the failing test for PIN derivation**

```csharp
// src/windows/Mesh.Tests/PinDerivationTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class PinDerivationTests
{
    private const string FpA = "a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4e5";
    private const string FpB = "0123456789abcdef110123456789abcdef110123456789abcdef110123456789"[..64];
    private const string FpF = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";
    private const string FpZero = "0000000000000000000000000000000000000000000000000000000000000";

    [Fact]
    public void Derive_IsOrderIndependent_ForKnownVector()
    {
        Assert.Equal("936941", PinDerivation.Derive(FpA, FpB));
        Assert.Equal("936941", PinDerivation.Derive(FpB, FpA));
    }

    [Fact]
    public void Derive_MatchesSecondKnownVector()
    {
        Assert.Equal("859565", PinDerivation.Derive(FpF, FpZero));
    }

    [Fact]
    public void Derive_DiffersForDifferentFingerprints()
    {
        var pin1 = PinDerivation.Derive(FpA, FpB);
        var pin2 = PinDerivation.Derive(FpA, FpF);
        Assert.NotEqual(pin1, pin2);
    }

    [Fact]
    public void Derive_IsAlwaysSixDigits()
    {
        var pin = PinDerivation.Derive(FpA, FpF);
        Assert.Equal(6, pin.Length);
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PinDerivationTests`
Expected: FAIL with "The type or namespace name 'PinDerivation' could not be found"

- [ ] **Step 4: Implement PinDerivation**

```csharp
// src/windows/Mesh.Core/PinDerivation.cs
using System.Security.Cryptography;
using System.Text;

namespace Mesh.Core;

public static class PinDerivation
{
    public static string Derive(string fingerprintA, string fingerprintB)
    {
        var ordered = new[] { fingerprintA, fingerprintB };
        Array.Sort(ordered, StringComparer.Ordinal);
        var combined = ordered[0] + ordered[1];
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(combined));
        var num = ((hash[0] << 16) | (hash[1] << 8) | hash[2]) % 1_000_000;
        return num.ToString("D6");
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PinDerivationTests`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/windows
git commit -m "feat(windows): scaffold solution and PIN derivation"
```

---

## Task 2: Windows identity (self-signed certificate)

**Files:**
- Create: `src/windows/Mesh.Core/IdentityStore.cs`
- Create: `src/windows/Mesh.Tests/IdentityStoreTests.cs`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Mesh.Core.IdentityStore.LoadOrCreate(string pfxPath) -> X509Certificate2` (cert has a private key attached). `Mesh.Core.IdentityStore.Fingerprint(X509Certificate2 cert) -> string` (lowercase hex SHA-256, 64 chars).

- [ ] **Step 1: Write the failing test**

```csharp
// src/windows/Mesh.Tests/IdentityStoreTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class IdentityStoreTests
{
    [Fact]
    public void LoadOrCreate_CreatesCertWithPrivateKey_WhenFileMissing()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.pfx");
        try
        {
            var cert = IdentityStore.LoadOrCreate(path);
            Assert.True(cert.HasPrivateKey);
            Assert.True(File.Exists(path));
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }

    [Fact]
    public void LoadOrCreate_ReturnsSameIdentity_OnSecondCall()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.pfx");
        try
        {
            var first = IdentityStore.LoadOrCreate(path);
            var second = IdentityStore.LoadOrCreate(path);
            Assert.Equal(IdentityStore.Fingerprint(first), IdentityStore.Fingerprint(second));
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }

    [Fact]
    public void Fingerprint_Is64LowercaseHexChars()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.pfx");
        try
        {
            var cert = IdentityStore.LoadOrCreate(path);
            var fp = IdentityStore.Fingerprint(cert);
            Assert.Equal(64, fp.Length);
            Assert.Equal(fp, fp.ToLowerInvariant());
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter IdentityStoreTests`
Expected: FAIL with "The type or namespace name 'IdentityStore' could not be found"

- [ ] **Step 3: Implement IdentityStore**

```csharp
// src/windows/Mesh.Core/IdentityStore.cs
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

namespace Mesh.Core;

public static class IdentityStore
{
    public static X509Certificate2 LoadOrCreate(string pfxPath)
    {
        if (File.Exists(pfxPath))
        {
            return new X509Certificate2(pfxPath, (string?)null,
                X509KeyStorageFlags.Exportable | X509KeyStorageFlags.PersistKeySet);
        }

        using var rsa = RSA.Create(2048);
        var request = new CertificateRequest(
            "CN=MeshDevice",
            rsa,
            HashAlgorithmName.SHA256,
            RSASignaturePadding.Pkcs1);

        var cert = request.CreateSelfSigned(
            DateTimeOffset.UtcNow.AddDays(-1),
            DateTimeOffset.UtcNow.AddYears(10));

        var exportable = new X509Certificate2(
            cert.Export(X509ContentType.Pfx),
            (string?)null,
            X509KeyStorageFlags.Exportable | X509KeyStorageFlags.PersistKeySet);

        Directory.CreateDirectory(Path.GetDirectoryName(pfxPath)!);
        File.WriteAllBytes(pfxPath, exportable.Export(X509ContentType.Pfx));
        return exportable;
    }

    public static string Fingerprint(X509Certificate2 cert)
    {
        var hash = SHA256.HashData(cert.RawData);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter IdentityStoreTests`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/windows
git commit -m "feat(windows): self-signed identity certificate store"
```

---

## Task 3: Windows paired-device store

**Files:**
- Create: `src/windows/Mesh.Core/PairedDevice.cs`
- Create: `src/windows/Mesh.Core/PairedDeviceStore.cs`
- Create: `src/windows/Mesh.Tests/PairedDeviceStoreTests.cs`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Mesh.Core.PairedDevice { string Uuid, string Name, string Fingerprint, string LastIp, DateTimeOffset PairedAt }`. `Mesh.Core.PairedDeviceStore.Load(string path) -> List<PairedDevice>`. `Mesh.Core.PairedDeviceStore.Save(string path, List<PairedDevice> devices)`. `Mesh.Core.PairedDeviceStore.Upsert(string path, PairedDevice device)`.

- [ ] **Step 1: Write the failing test**

```csharp
// src/windows/Mesh.Tests/PairedDeviceStoreTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class PairedDeviceStoreTests
{
    [Fact]
    public void Load_ReturnsEmptyList_WhenFileMissing()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        var result = PairedDeviceStore.Load(path);
        Assert.Empty(result);
    }

    [Fact]
    public void Load_ReturnsEmptyList_WhenFileCorrupt()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        File.WriteAllText(path, "{not valid json");
        try
        {
            var result = PairedDeviceStore.Load(path);
            Assert.Empty(result);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Upsert_ThenLoad_RoundTrips()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        try
        {
            var device = new PairedDevice
            {
                Uuid = "device-1",
                Name = "Pixel",
                Fingerprint = "abc123",
                LastIp = "192.168.1.5",
                PairedAt = DateTimeOffset.Parse("2026-10-13T00:00:00Z")
            };
            PairedDeviceStore.Upsert(path, device);
            var loaded = PairedDeviceStore.Load(path);
            Assert.Single(loaded);
            Assert.Equal("device-1", loaded[0].Uuid);
            Assert.Equal("abc123", loaded[0].Fingerprint);
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }

    [Fact]
    public void Upsert_ReplacesExistingUuid_RatherThanDuplicating()
    {
        var path = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        try
        {
            var first = new PairedDevice { Uuid = "d1", Name = "Old", Fingerprint = "fp1", LastIp = "1.1.1.1", PairedAt = DateTimeOffset.UtcNow };
            var second = new PairedDevice { Uuid = "d1", Name = "New", Fingerprint = "fp2", LastIp = "2.2.2.2", PairedAt = DateTimeOffset.UtcNow };
            PairedDeviceStore.Upsert(path, first);
            PairedDeviceStore.Upsert(path, second);
            var loaded = PairedDeviceStore.Load(path);
            Assert.Single(loaded);
            Assert.Equal("fp2", loaded[0].Fingerprint);
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PairedDeviceStoreTests`
Expected: FAIL with "The type or namespace name 'PairedDevice' could not be found"

- [ ] **Step 3: Implement PairedDevice and PairedDeviceStore**

```csharp
// src/windows/Mesh.Core/PairedDevice.cs
namespace Mesh.Core;

public class PairedDevice
{
    public required string Uuid { get; set; }
    public required string Name { get; set; }
    public required string Fingerprint { get; set; }
    public required string LastIp { get; set; }
    public required DateTimeOffset PairedAt { get; set; }
}
```

```csharp
// src/windows/Mesh.Core/PairedDeviceStore.cs
using System.Text.Json;

namespace Mesh.Core;

public static class PairedDeviceStore
{
    public static List<PairedDevice> Load(string path)
    {
        if (!File.Exists(path)) return new List<PairedDevice>();
        try
        {
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<List<PairedDevice>>(json) ?? new List<PairedDevice>();
        }
        catch (JsonException)
        {
            return new List<PairedDevice>();
        }
    }

    public static void Save(string path, List<PairedDevice> devices)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var json = JsonSerializer.Serialize(devices);
        File.WriteAllText(path, json);
    }

    public static void Upsert(string path, PairedDevice device)
    {
        var devices = Load(path);
        devices.RemoveAll(d => d.Uuid == device.Uuid);
        devices.Add(device);
        Save(path, devices);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PairedDeviceStoreTests`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/windows
git commit -m "feat(windows): paired-device JSON store"
```

---

## Task 4: Windows mDNS advertise + browse

**Files:**
- Modify: `src/windows/Mesh.Core/Mesh.Core.csproj` (add `Makaretu.Dns` package reference)
- Create: `src/windows/Mesh.Core/MeshDiscovery.cs`
- Create: `src/windows/Mesh.Tests/MeshDiscoveryTests.cs`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Mesh.Core.DiscoveredDevice { string Uuid, string Name, string Platform, string IpAddress, int Port }`. `Mesh.Core.MeshDiscovery` with `Advertise(string uuid, string name, string platform, int port)`, `StartBrowsing(Action<DiscoveredDevice> onFound)`, `Stop()`.

- [ ] **Step 1: Add the Makaretu.Dns package**

```bash
cd src/windows/Mesh.Core && dotnet add package Makaretu.Dns
```

- [ ] **Step 2: Write the failing test (local round-trip, not mocked — mDNS loopback is the real integration surface)**

```csharp
// src/windows/Mesh.Tests/MeshDiscoveryTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class MeshDiscoveryTests
{
    [Fact]
    public async Task Advertise_IsFoundByBrowse_OnLoopback()
    {
        var found = new TaskCompletionSource<DiscoveredDevice>();
        using var browser = new MeshDiscovery();
        browser.StartBrowsing(device =>
        {
            if (device.Uuid == "test-uuid-1") found.TrySetResult(device);
        });

        using var advertiser = new MeshDiscovery();
        advertiser.Advertise("test-uuid-1", "TestPC", "windows", 5555);

        var result = await Task.WhenAny(found.Task, Task.Delay(TimeSpan.FromSeconds(10)));
        Assert.Same(found.Task, result);
        var device = await found.Task;
        Assert.Equal("TestPC", device.Name);
        Assert.Equal("windows", device.Platform);
        Assert.Equal(5555, device.Port);
    }

    [Fact]
    public void Advertise_DoesNotThrow_WhenCalledTwiceWithSamePort()
    {
        using var advertiser = new MeshDiscovery();
        advertiser.Advertise("test-uuid-2", "TestPC2", "windows", 5556);
        advertiser.Advertise("test-uuid-2", "TestPC2", "windows", 5556);
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshDiscoveryTests`
Expected: FAIL with "The type or namespace name 'MeshDiscovery' could not be found"

- [ ] **Step 4: Implement MeshDiscovery**

```csharp
// src/windows/Mesh.Core/MeshDiscovery.cs
using Makaretu.Dns;

namespace Mesh.Core;

public class DiscoveredDevice
{
    public required string Uuid { get; set; }
    public required string Name { get; set; }
    public required string Platform { get; set; }
    public required string IpAddress { get; set; }
    public required int Port { get; set; }
}

public class MeshDiscovery : IDisposable
{
    private const string ServiceType = "_meshlink._tcp";
    private MulticastService? _mdns;
    private ServiceDiscovery? _discovery;
    private bool _advertised;

    public void Advertise(string uuid, string name, string platform, int port)
    {
        if (_advertised) return;
        _mdns ??= new MulticastService();
        _discovery ??= new ServiceDiscovery(_mdns);

        var profile = new ServiceProfile(name, ServiceType, (ushort)port);
        profile.AddProperty("id", uuid);
        profile.AddProperty("name", name);
        profile.AddProperty("platform", platform);

        _discovery.Advertise(profile);
        _mdns.Start();
        _advertised = true;
    }

    public void StartBrowsing(Action<DiscoveredDevice> onFound)
    {
        _mdns ??= new MulticastService();
        _discovery ??= new ServiceDiscovery(_mdns);

        _discovery.ServiceInstanceDiscovered += (s, e) =>
        {
            _mdns!.SendQuery(e.ServiceInstanceName, type: Makaretu.Dns.DnsType.TXT);
        };

        _mdns.AnswerReceived += (s, e) =>
        {
            var txtRecords = e.Message.Answers.OfType<TXTRecord>();
            foreach (var txt in txtRecords)
            {
                var props = txt.Strings
                    .Select(s2 => s2.Split('=', 2))
                    .Where(parts => parts.Length == 2)
                    .ToDictionary(parts => parts[0], parts => parts[1]);

                if (!props.TryGetValue("id", out var uuid)) continue;

                var address = e.Message.AdditionalRecords.OfType<ARecord>().FirstOrDefault();
                var srv = e.Message.AdditionalRecords.OfType<SRVRecord>().FirstOrDefault();
                if (address == null || srv == null) continue;

                onFound(new DiscoveredDevice
                {
                    Uuid = uuid,
                    Name = props.GetValueOrDefault("name", uuid),
                    Platform = props.GetValueOrDefault("platform", "unknown"),
                    IpAddress = address.Address.ToString(),
                    Port = srv.Port
                });
            }
        };

        _mdns.Start();
    }

    public void Stop()
    {
        _mdns?.Stop();
    }

    public void Dispose()
    {
        Stop();
        _discovery?.Dispose();
        _mdns?.Dispose();
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshDiscoveryTests`
Expected: PASS (2 tests). If the loopback discovery test is flaky in the sandbox (no real network/multicast support in CI containers), mark it `[Fact(Skip = "requires multicast-capable network")]` and rely on manual testing per the spec's Testing section — note this in the commit message if skipped.

- [ ] **Step 6: Commit**

```bash
git add src/windows
git commit -m "feat(windows): mDNS advertise and browse via Makaretu.Dns"
```

---

## Task 5: Windows TLS pairing session (handshake, fingerprint check, PIN flow)

**Files:**
- Create: `src/windows/Mesh.Core/PairingSession.cs`
- Create: `src/windows/Mesh.Tests/PairingSessionTests.cs`

**Interfaces:**
- Consumes: `IdentityStore.LoadOrCreate`, `IdentityStore.Fingerprint`, `PinDerivation.Derive`, `PairedDeviceStore`.
- Produces: `Mesh.Core.PairingSession` with:
  - `StartListener(X509Certificate2 identity, int port) -> Task` (accepts one incoming TLS connection, exposes `PeerFingerprint`).
  - `ConnectTo(X509Certificate2 identity, string ip, int port) -> Task` (opens outgoing TLS connection, exposes `PeerFingerprint`).
  - `ComputePin() -> string` (derives PIN from own + peer fingerprint via `PinDerivation.Derive`).
  - `IsPeerTrusted(string path, string uuid) -> bool` (compares `PeerFingerprint` against stored record for `uuid`; false if no record or mismatch).

- [ ] **Step 1: Write the failing test for untrusted handshake + PIN**

```csharp
// src/windows/Mesh.Tests/PairingSessionTests.cs
using Mesh.Core;
using System.Net;
using Xunit;

namespace Mesh.Tests;

public class PairingSessionTests
{
    [Fact]
    public async Task Handshake_BothSidesComputeSamePin()
    {
        var certAPath = Path.Combine(Path.GetTempPath(), $"mesh-test-a-{Guid.NewGuid()}.pfx");
        var certBPath = Path.Combine(Path.GetTempPath(), $"mesh-test-b-{Guid.NewGuid()}.pfx");
        try
        {
            var certA = IdentityStore.LoadOrCreate(certAPath);
            var certB = IdentityStore.LoadOrCreate(certBPath);

            const int port = 51234;
            var server = new PairingSession();
            var listenTask = server.StartListener(certA, port);

            await Task.Delay(200); // let the listener bind
            var client = new PairingSession();
            await client.ConnectTo(certB, IPAddress.Loopback.ToString(), port);
            await listenTask;

            var serverPin = server.ComputePin();
            var clientPin = client.ComputePin();
            Assert.Equal(serverPin, clientPin);
        }
        finally
        {
            if (File.Exists(certAPath)) File.Delete(certAPath);
            if (File.Exists(certBPath)) File.Delete(certBPath);
        }
    }

    [Fact]
    public void IsPeerTrusted_ReturnsFalse_WhenNoStoredRecord()
    {
        var storePath = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        var session = new PairingSession();
        Assert.False(session.IsPeerTrusted(storePath, "unknown-uuid"));
    }

    [Fact]
    public void IsPeerTrusted_ReturnsFalse_WhenFingerprintChanged()
    {
        var storePath = Path.Combine(Path.GetTempPath(), $"mesh-test-{Guid.NewGuid()}.json");
        try
        {
            PairedDeviceStore.Upsert(storePath, new PairedDevice
            {
                Uuid = "known-uuid",
                Name = "Old Device",
                Fingerprint = "old-fingerprint",
                LastIp = "1.2.3.4",
                PairedAt = DateTimeOffset.UtcNow
            });

            var session = new PairingSession();
            // Simulate a session whose peer fingerprint differs from storage.
            typeof(PairingSession).GetProperty("PeerFingerprint")!
                .SetValue(session, "new-fingerprint");

            Assert.False(session.IsPeerTrusted(storePath, "known-uuid"));
        }
        finally
        {
            if (File.Exists(storePath)) File.Delete(storePath);
        }
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PairingSessionTests`
Expected: FAIL with "The type or namespace name 'PairingSession' could not be found"

- [ ] **Step 3: Implement PairingSession**

```csharp
// src/windows/Mesh.Core/PairingSession.cs
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography.X509Certificates;

namespace Mesh.Core;

public class PairingSession
{
    public string? PeerFingerprint { get; set; }
    private X509Certificate2? _localIdentity;

    public async Task StartListener(X509Certificate2 identity, int port)
    {
        _localIdentity = identity;
        var listener = new TcpListener(IPAddress.Any, port);
        listener.Start();
        using var client = await listener.AcceptTcpClientAsync()
            .WaitAsync(TimeSpan.FromSeconds(10));
        listener.Stop();

        using var sslStream = new SslStream(client.GetStream(), false,
            (sender, cert, chain, errors) => true); // untrusted at handshake stage, per spec

        await sslStream.AuthenticateAsServerAsync(identity, clientCertificateRequired: true,
            checkCertificateRevocation: false);

        var peerCert = sslStream.RemoteCertificate as X509Certificate2
            ?? new X509Certificate2(sslStream.RemoteCertificate!);
        PeerFingerprint = IdentityStore.Fingerprint(peerCert);
    }

    public async Task ConnectTo(X509Certificate2 identity, string ip, int port)
    {
        _localIdentity = identity;
        using var client = new TcpClient();
        await client.ConnectAsync(ip, port).WaitAsync(TimeSpan.FromSeconds(10));

        using var sslStream = new SslStream(client.GetStream(), false,
            (sender, cert, chain, errors) => true); // untrusted at handshake stage, per spec

        var clientCerts = new X509Certificate2Collection(identity);
        await sslStream.AuthenticateAsClientAsync(new SslClientAuthenticationOptions
        {
            TargetHost = ip,
            ClientCertificates = clientCerts,
            RemoteCertificateValidationCallback = (sender, cert, chain, errors) => true
        });

        var peerCert = sslStream.RemoteCertificate as X509Certificate2
            ?? new X509Certificate2(sslStream.RemoteCertificate!);
        PeerFingerprint = IdentityStore.Fingerprint(peerCert);
    }

    public string ComputePin()
    {
        if (_localIdentity == null || PeerFingerprint == null)
            throw new InvalidOperationException("Handshake has not completed yet.");
        var ownFingerprint = IdentityStore.Fingerprint(_localIdentity);
        return PinDerivation.Derive(ownFingerprint, PeerFingerprint);
    }

    public bool IsPeerTrusted(string pairedDevicesPath, string uuid)
    {
        var devices = PairedDeviceStore.Load(pairedDevicesPath);
        var record = devices.FirstOrDefault(d => d.Uuid == uuid);
        return record != null && record.Fingerprint == PeerFingerprint;
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter PairingSessionTests`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/windows
git commit -m "feat(windows): TLS pairing session with fingerprint-based PIN and trust check"
```

---

## Task 6: Windows UI (device list, PIN confirmation, connect flow)

**Files:**
- Modify: `src/windows/Mesh.App/MainWindow.xaml`
- Modify: `src/windows/Mesh.App/MainWindow.xaml.cs`
- Create: `src/windows/Mesh.App/PinConfirmWindow.xaml`
- Create: `src/windows/Mesh.App/PinConfirmWindow.xaml.cs`

**Interfaces:**
- Consumes: `Mesh.Core.MeshDiscovery`, `Mesh.Core.PairingSession`, `Mesh.Core.IdentityStore`, `Mesh.Core.PairedDeviceStore`, `Mesh.Core.PairedDevice`.
- Produces: none consumed by later tasks (UI is a leaf in this sub-project).

- [ ] **Step 1: Write MainWindow.xaml with a device list and a Connect button**

```xml
<!-- src/windows/Mesh.App/MainWindow.xaml -->
<Window x:Class="Mesh.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Mesh" Height="450" Width="400">
    <Grid Margin="12">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        <TextBlock Grid.Row="0" Text="Discovered devices" FontWeight="Bold" Margin="0,0,0,8"/>
        <ListBox Grid.Row="1" Name="DeviceListBox" DisplayMemberPath="Name"/>
        <Button Grid.Row="2" Name="ConnectButton" Content="Connect" Margin="0,8,0,0" Click="ConnectButton_Click"/>
    </Grid>
</Window>
```

- [ ] **Step 2: Write MainWindow.xaml.cs wiring discovery into the list and launching pairing**

```csharp
// src/windows/Mesh.App/MainWindow.xaml.cs
using System.IO;
using System.Windows;
using Mesh.Core;

namespace Mesh.App;

public partial class MainWindow : Window
{
    private readonly MeshDiscovery _discovery = new();
    private readonly List<DiscoveredDevice> _devices = new();
    private readonly string _identityPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Mesh", "identity.pfx");
    private readonly string _pairedDevicesPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Mesh", "paired_devices.json");

    public MainWindow()
    {
        InitializeComponent();
        var identity = IdentityStore.LoadOrCreate(_identityPath);
        var selfUuid = Guid.NewGuid().ToString(); // stable per-install id; persisted separately in a future task
        _discovery.Advertise(selfUuid, Environment.MachineName, "windows", 51555);
        _discovery.StartBrowsing(device =>
        {
            Dispatcher.Invoke(() =>
            {
                if (_devices.Any(d => d.Uuid == device.Uuid)) return;
                _devices.Add(device);
                DeviceListBox.Items.Add(device);
            });
        });
    }

    private async void ConnectButton_Click(object sender, RoutedEventArgs e)
    {
        if (DeviceListBox.SelectedItem is not DiscoveredDevice target) return;

        var identity = IdentityStore.LoadOrCreate(_identityPath);
        var session = new PairingSession();
        try
        {
            await session.ConnectTo(identity, target.IpAddress, target.Port);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Connection failed: {ex.Message}");
            return;
        }

        if (session.IsPeerTrusted(_pairedDevicesPath, target.Uuid))
        {
            MessageBox.Show($"Reconnected to {target.Name} (trusted).");
            return;
        }

        var pin = session.ComputePin();
        var pinWindow = new PinConfirmWindow(pin);
        var confirmed = pinWindow.ShowDialog() == true;
        if (!confirmed)
        {
            MessageBox.Show("Pairing failed.");
            return;
        }

        PairedDeviceStore.Upsert(_pairedDevicesPath, new PairedDevice
        {
            Uuid = target.Uuid,
            Name = target.Name,
            Fingerprint = session.PeerFingerprint!,
            LastIp = target.IpAddress,
            PairedAt = DateTimeOffset.UtcNow
        });
        MessageBox.Show($"Paired with {target.Name}.");
    }
}
```

- [ ] **Step 3: Write PinConfirmWindow.xaml**

```xml
<!-- src/windows/Mesh.App/PinConfirmWindow.xaml -->
<Window x:Class="Mesh.App.PinConfirmWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Confirm PIN" Height="180" Width="300" WindowStartupLocation="CenterScreen">
    <StackPanel Margin="16">
        <TextBlock Text="Does this PIN match the other device?" TextWrapping="Wrap" Margin="0,0,0,12"/>
        <TextBlock Name="PinText" FontSize="28" FontWeight="Bold" HorizontalAlignment="Center" Margin="0,0,0,16"/>
        <StackPanel Orientation="Horizontal" HorizontalAlignment="Center">
            <Button Name="MatchButton" Content="Match" Width="100" Margin="0,0,8,0" Click="MatchButton_Click"/>
            <Button Name="NoMatchButton" Content="Not matching" Width="120" Click="NoMatchButton_Click"/>
        </StackPanel>
    </StackPanel>
</Window>
```

- [ ] **Step 4: Write PinConfirmWindow.xaml.cs**

```csharp
// src/windows/Mesh.App/PinConfirmWindow.xaml.cs
using System.Windows;

namespace Mesh.App;

public partial class PinConfirmWindow : Window
{
    public PinConfirmWindow(string pin)
    {
        InitializeComponent();
        PinText.Text = pin;
    }

    private void MatchButton_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = true;
        Close();
    }

    private void NoMatchButton_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
```

- [ ] **Step 5: Build to verify it compiles**

Run: `cd src/windows && dotnet build Mesh.App`
Expected: Build succeeded, 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/windows
git commit -m "feat(windows): device list UI with PIN confirmation dialog"
```

---

## Task 7: Scaffold Android project structure

**Files:**
- Create: `android/settings.gradle.kts`
- Create: `android/build.gradle.kts`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/com/mesh/core/PinDerivation.kt`
- Create: `android/app/src/test/java/com/mesh/core/PinDerivationTest.kt`

**Interfaces:**
- Produces: `com.mesh.core.PinDerivation.derive(fingerprintA: String, fingerprintB: String): String`.

- [ ] **Step 1: Create the Gradle project skeleton**

```kotlin
// android/settings.gradle.kts
rootProject.name = "Mesh"
include(":app")
```

```kotlin
// android/build.gradle.kts
plugins {
    id("com.android.application") version "8.5.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
```

```kotlin
// android/app/build.gradle.kts
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.mesh"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mesh"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
```

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
    <uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_STATE"/>

    <application
        android:label="Mesh"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="true">
        <activity
            android:name=".ui.MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- [ ] **Step 2: Write the failing test for PIN derivation (same algorithm, same vectors as Windows)**

```kotlin
// android/app/src/test/java/com/mesh/core/PinDerivationTest.kt
package com.mesh.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class PinDerivationTest {
    private val fpA = "a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4e5f6071829a1b2c3d4e5"
    private val fpB = "0123456789abcdef110123456789abcdef110123456789abcdef110123456789".take(64)
    private val fpF = "f".repeat(64)
    private val fpZero = "0".repeat(64)

    @Test
    fun `derive is order independent for known vector`() {
        assertEquals("936941", PinDerivation.derive(fpA, fpB))
        assertEquals("936941", PinDerivation.derive(fpB, fpA))
    }

    @Test
    fun `derive matches second known vector`() {
        assertEquals("859565", PinDerivation.derive(fpF, fpZero))
    }

    @Test
    fun `derive differs for different fingerprints`() {
        val pin1 = PinDerivation.derive(fpA, fpB)
        val pin2 = PinDerivation.derive(fpA, fpF)
        assertNotEquals(pin1, pin2)
    }

    @Test
    fun `derive is always six digits`() {
        assertEquals(6, PinDerivation.derive(fpA, fpF).length)
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mesh.core.PinDerivationTest"`
Expected: FAIL — compilation error, `PinDerivation` unresolved.

- [ ] **Step 4: Implement PinDerivation**

```kotlin
// android/app/src/main/java/com/mesh/core/PinDerivation.kt
package com.mesh.core

import java.security.MessageDigest

object PinDerivation {
    fun derive(fingerprintA: String, fingerprintB: String): String {
        val ordered = listOf(fingerprintA, fingerprintB).sorted()
        val combined = (ordered[0] + ordered[1]).toByteArray(Charsets.UTF_8)
        val hash = MessageDigest.getInstance("SHA-256").digest(combined)
        val num = (((hash[0].toInt() and 0xFF) shl 16) or
                   ((hash[1].toInt() and 0xFF) shl 8) or
                   (hash[2].toInt() and 0xFF)) % 1_000_000
        return num.toString().padStart(6, '0')
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests "com.mesh.core.PinDerivationTest"`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add android
git commit -m "feat(android): scaffold Gradle project and PIN derivation"
```

---

## Task 8: Android identity (Keystore-backed certificate)

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/IdentityStore.kt`
- Create: `android/app/src/androidTest/java/com/mesh/core/IdentityStoreTest.kt`

**Interfaces:**
- Consumes: nothing new.
- Produces: `com.mesh.core.IdentityStore.loadOrCreate(context: Context): Pair<X509Certificate, PrivateKey>`. `com.mesh.core.IdentityStore.fingerprint(cert: X509Certificate): String` (lowercase hex SHA-256, 64 chars).

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
// android/app/src/androidTest/java/com/mesh/core/IdentityStoreTest.kt
package com.mesh.core

import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class IdentityStoreTest {
    @Test
    fun loadOrCreate_returnsSameFingerprint_onSecondCall() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val (certFirst, _) = IdentityStore.loadOrCreate(context)
        val (certSecond, _) = IdentityStore.loadOrCreate(context)
        assertEquals(IdentityStore.fingerprint(certFirst), IdentityStore.fingerprint(certSecond))
    }

    @Test
    fun fingerprint_is64LowercaseHexChars() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val (cert, _) = IdentityStore.loadOrCreate(context)
        val fp = IdentityStore.fingerprint(cert)
        assertEquals(64, fp.length)
        assertTrue(fp == fp.lowercase())
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.IdentityStoreTest"`
Expected: FAIL — compilation error, `IdentityStore` unresolved.

- [ ] **Step 3: Implement IdentityStore**

```kotlin
// android/app/src/main/java/com/mesh/core/IdentityStore.kt
package com.mesh.core

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.math.BigInteger
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.cert.X509Certificate
import java.util.Date
import javax.security.auth.x500.X500Principal

object IdentityStore {
    private const val KEYSTORE_ALIAS = "mesh_identity"

    fun loadOrCreate(context: Context): Pair<X509Certificate, PrivateKey> {
        val keyStore = KeyStore.getInstance("AndroidKeyStore")
        keyStore.load(null)

        if (keyStore.containsAlias(KEYSTORE_ALIAS)) {
            val cert = keyStore.getCertificate(KEYSTORE_ALIAS) as X509Certificate
            val privateKey = keyStore.getKey(KEYSTORE_ALIAS, null) as PrivateKey
            return Pair(cert, privateKey)
        }

        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore")
        val now = Date()
        val expiry = Date(now.time + 10L * 365 * 24 * 60 * 60 * 1000)

        val spec = KeyGenParameterSpec.Builder(
            KEYSTORE_ALIAS,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setKeySize(2048)
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
            .setCertificateSubject(X500Principal("CN=MeshDevice"))
            .setCertificateSerialNumber(BigInteger.ONE)
            .setCertificateNotBefore(now)
            .setCertificateNotAfter(expiry)
            .build()

        generator.initialize(spec)
        generator.generateKeyPair()

        val cert = keyStore.getCertificate(KEYSTORE_ALIAS) as X509Certificate
        val privateKey = keyStore.getKey(KEYSTORE_ALIAS, null) as PrivateKey
        return Pair(cert, privateKey)
    }

    fun fingerprint(cert: X509Certificate): String {
        val hash = MessageDigest.getInstance("SHA-256").digest(cert.encoded)
        return hash.joinToString("") { "%02x".format(it) }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.IdentityStoreTest"`
Expected: PASS (2 tests). Requires a connected emulator/device — AndroidKeyStore is not available on the JVM unit-test runner, which is why this is an `androidTest`, not a `test`.

- [ ] **Step 5: Commit**

```bash
git add android
git commit -m "feat(android): Keystore-backed self-signed identity"
```

---

## Task 9: Android paired-device store (Room)

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/PairedDevice.kt`
- Create: `android/app/src/main/java/com/mesh/core/PairedDeviceDao.kt`
- Create: `android/app/src/main/java/com/mesh/core/MeshDatabase.kt`
- Create: `android/app/src/androidTest/java/com/mesh/core/PairedDeviceDaoTest.kt`

**Interfaces:**
- Consumes: nothing new.
- Produces: `com.mesh.core.PairedDevice(uuid: String, name: String, fingerprint: String, lastIp: String, pairedAt: Long)` (Room `@Entity`). `com.mesh.core.PairedDeviceDao` with `suspend fun upsert(device: PairedDevice)`, `suspend fun findByUuid(uuid: String): PairedDevice?`, `suspend fun all(): List<PairedDevice>`. `com.mesh.core.MeshDatabase.getInstance(context: Context): MeshDatabase`.

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
// android/app/src/androidTest/java/com/mesh/core/PairedDeviceDaoTest.kt
package com.mesh.core

import androidx.room.Room
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PairedDeviceDaoTest {
    private fun inMemoryDb(): MeshDatabase {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        return Room.inMemoryDatabaseBuilder(context, MeshDatabase::class.java).build()
    }

    @Test
    fun findByUuid_returnsNull_whenAbsent() = runBlocking {
        val db = inMemoryDb()
        assertNull(db.pairedDeviceDao().findByUuid("missing"))
    }

    @Test
    fun upsert_thenFindByUuid_roundTrips() = runBlocking {
        val db = inMemoryDb()
        val device = PairedDevice(
            uuid = "d1", name = "Pixel", fingerprint = "fp1",
            lastIp = "192.168.1.5", pairedAt = 1760000000000L
        )
        db.pairedDeviceDao().upsert(device)
        val loaded = db.pairedDeviceDao().findByUuid("d1")
        assertEquals("fp1", loaded?.fingerprint)
    }

    @Test
    fun upsert_replacesExistingUuid_ratherThanDuplicating() = runBlocking {
        val db = inMemoryDb()
        db.pairedDeviceDao().upsert(PairedDevice("d1", "Old", "fp1", "1.1.1.1", 1L))
        db.pairedDeviceDao().upsert(PairedDevice("d1", "New", "fp2", "2.2.2.2", 2L))
        val all = db.pairedDeviceDao().all()
        assertEquals(1, all.size)
        assertEquals("fp2", all[0].fingerprint)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.PairedDeviceDaoTest"`
Expected: FAIL — compilation error, `PairedDevice`/`MeshDatabase` unresolved.

- [ ] **Step 3: Implement the Room entity, DAO, and database**

```kotlin
// android/app/src/main/java/com/mesh/core/PairedDevice.kt
package com.mesh.core

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "paired_devices")
data class PairedDevice(
    @PrimaryKey val uuid: String,
    val name: String,
    val fingerprint: String,
    val lastIp: String,
    val pairedAt: Long
)
```

```kotlin
// android/app/src/main/java/com/mesh/core/PairedDeviceDao.kt
package com.mesh.core

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PairedDeviceDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(device: PairedDevice)

    @Query("SELECT * FROM paired_devices WHERE uuid = :uuid LIMIT 1")
    suspend fun findByUuid(uuid: String): PairedDevice?

    @Query("SELECT * FROM paired_devices")
    suspend fun all(): List<PairedDevice>
}
```

```kotlin
// android/app/src/main/java/com/mesh/core/MeshDatabase.kt
package com.mesh.core

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [PairedDevice::class], version = 1)
abstract class MeshDatabase : RoomDatabase() {
    abstract fun pairedDeviceDao(): PairedDeviceDao

    companion object {
        @Volatile private var instance: MeshDatabase? = null

        fun getInstance(context: Context): MeshDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(context, MeshDatabase::class.java, "mesh.db")
                    .build()
                    .also { instance = it }
            }
    }
}
```

- [ ] **Step 4: Add kotlinx-coroutines-test and ksp plugin needed by this task**

```kotlin
// android/app/build.gradle.kts — add to plugins block
id("com.google.devtools.ksp") version "1.9.24-1.0.20" apply false
```

```kotlin
// android/app/build.gradle.kts — add to dependencies block
testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
androidTestImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.PairedDeviceDaoTest"`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add android
git commit -m "feat(android): Room-backed paired-device store"
```

---

## Task 10: Android NSD discovery

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/MeshDiscovery.kt`
- Create: `android/app/src/androidTest/java/com/mesh/core/MeshDiscoveryTest.kt`

**Interfaces:**
- Consumes: nothing new.
- Produces: `com.mesh.core.DiscoveredDevice(uuid: String, name: String, platform: String, ipAddress: String, port: Int)`. `com.mesh.core.MeshDiscovery(context: Context)` with `fun advertise(uuid: String, name: String, platform: String, port: Int)`, `fun startBrowsing(onFound: (DiscoveredDevice) -> Unit)`, `fun stop()`.

- [ ] **Step 1: Write the failing instrumented test (loopback discovery, same shape as Task 4's Windows test)**

```kotlin
// android/app/src/androidTest/java/com/mesh/core/MeshDiscoveryTest.kt
package com.mesh.core

import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeoutOrNull
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class MeshDiscoveryTest {
    @Test
    fun advertise_isFoundByBrowse_onLocalNetwork() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val found = CompletableDeferred<DiscoveredDevice>()

        val browser = MeshDiscovery(context)
        browser.startBrowsing { device ->
            if (device.uuid == "test-uuid-1" && !found.isCompleted) found.complete(device)
        }

        val advertiser = MeshDiscovery(context)
        advertiser.advertise("test-uuid-1", "TestPhone", "android", 5555)

        val result = withTimeoutOrNull(10_000) { found.await() }
        browser.stop()
        advertiser.stop()

        assertNotNull(result)
        assertEquals("TestPhone", result?.name)
        assertEquals("android", result?.platform)
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.MeshDiscoveryTest"`
Expected: FAIL — compilation error, `MeshDiscovery` unresolved.

- [ ] **Step 3: Implement MeshDiscovery**

```kotlin
// android/app/src/main/java/com/mesh/core/MeshDiscovery.kt
package com.mesh.core

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo

data class DiscoveredDevice(
    val uuid: String,
    val name: String,
    val platform: String,
    val ipAddress: String,
    val port: Int
)

class MeshDiscovery(context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val serviceType = "_meshlink._tcp."
    private var registrationListener: NsdManager.RegistrationListener? = null
    private var discoveryListener: NsdManager.DiscoveryListener? = null

    fun advertise(uuid: String, name: String, platform: String, port: Int) {
        val serviceInfo = NsdServiceInfo().apply {
            serviceName = name
            this.serviceType = this@MeshDiscovery.serviceType
            this.port = port
            setAttribute("id", uuid)
            setAttribute("name", name)
            setAttribute("platform", platform)
        }

        val listener = object : NsdManager.RegistrationListener {
            override fun onServiceRegistered(info: NsdServiceInfo) {}
            override fun onRegistrationFailed(info: NsdServiceInfo, errorCode: Int) {}
            override fun onServiceUnregistered(info: NsdServiceInfo) {}
            override fun onUnregistrationFailed(info: NsdServiceInfo, errorCode: Int) {}
        }
        registrationListener = listener
        nsdManager.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, listener)
    }

    fun startBrowsing(onFound: (DiscoveredDevice) -> Unit) {
        val listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {}
            override fun onDiscoveryStopped(serviceType: String) {}
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}

            override fun onServiceFound(service: NsdServiceInfo) {
                nsdManager.resolveService(service, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(info: NsdServiceInfo, errorCode: Int) {}
                    override fun onServiceResolved(info: NsdServiceInfo) {
                        val uuid = info.attributes["id"]?.toString(Charsets.UTF_8) ?: return
                        val name = info.attributes["name"]?.toString(Charsets.UTF_8) ?: uuid
                        val platform = info.attributes["platform"]?.toString(Charsets.UTF_8) ?: "unknown"
                        onFound(DiscoveredDevice(uuid, name, platform, info.host.hostAddress ?: "", info.port))
                    }
                })
            }

            override fun onServiceLost(service: NsdServiceInfo) {}
        }
        discoveryListener = listener
        nsdManager.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, listener)
    }

    fun stop() {
        registrationListener?.let { nsdManager.unregisterService(it) }
        discoveryListener?.let { nsdManager.stopServiceDiscovery(it) }
        registrationListener = null
        discoveryListener = null
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.MeshDiscoveryTest"`
Expected: PASS (1 test). This requires a device/emulator with multicast-capable Wi-Fi; if the test runner's network sandbox blocks multicast, document the skip (`@Ignore("requires multicast-capable network")`) and rely on manual verification per the spec's Testing section.

- [ ] **Step 5: Commit**

```bash
git add android
git commit -m "feat(android): NSD-based mDNS advertise and browse"
```

---

## Task 11: Android TLS pairing session (handshake, fingerprint check, PIN flow)

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/PairingSession.kt`
- Create: `android/app/src/androidTest/java/com/mesh/core/PairingSessionTest.kt`

**Interfaces:**
- Consumes: `IdentityStore.loadOrCreate`, `IdentityStore.fingerprint`, `PinDerivation.derive`, `MeshDatabase`/`PairedDeviceDao`.
- Produces: `com.mesh.core.PairingSession` with:
  - `suspend fun startListener(identity: Pair<X509Certificate, PrivateKey>, port: Int)`
  - `suspend fun connectTo(identity: Pair<X509Certificate, PrivateKey>, ip: String, port: Int)`
  - `fun computePin(localCert: X509Certificate): String`
  - `suspend fun isPeerTrusted(dao: PairedDeviceDao, uuid: String): Boolean`
  - `var peerFingerprint: String?`

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
// android/app/src/androidTest/java/com/mesh/core/PairingSessionTest.kt
package com.mesh.core

import androidx.room.Room
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class PairingSessionTest {
    @Test
    fun handshake_bothSidesComputeSamePin() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val identityA = IdentityStore.loadOrCreate(context)
        val identityB = IdentityStore.loadOrCreate(context) // same alias in this test env; real devices differ per-install

        val port = 51234
        val server = PairingSession()
        val serverJob = async { server.startListener(identityA, port) }

        delay(200)
        val client = PairingSession()
        client.connectTo(identityB, "127.0.0.1", port)
        serverJob.await()

        val serverPin = server.computePin(identityA.first)
        val clientPin = client.computePin(identityB.first)
        assertEquals(serverPin, clientPin)
    }

    @Test
    fun isPeerTrusted_returnsFalse_whenNoStoredRecord() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val db = Room.inMemoryDatabaseBuilder(context, MeshDatabase::class.java).build()
        val session = PairingSession()
        session.peerFingerprint = "some-fingerprint"
        assertFalse(session.isPeerTrusted(db.pairedDeviceDao(), "unknown-uuid"))
    }

    @Test
    fun isPeerTrusted_returnsFalse_whenFingerprintChanged() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val db = Room.inMemoryDatabaseBuilder(context, MeshDatabase::class.java).build()
        db.pairedDeviceDao().upsert(PairedDevice("known-uuid", "Old", "old-fingerprint", "1.2.3.4", 1L))

        val session = PairingSession()
        session.peerFingerprint = "new-fingerprint"
        assertFalse(session.isPeerTrusted(db.pairedDeviceDao(), "known-uuid"))
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.PairingSessionTest"`
Expected: FAIL — compilation error, `PairingSession` unresolved.

- [ ] **Step 3: Implement PairingSession**

```kotlin
// android/app/src/main/java/com/mesh/core/PairingSession.kt
package com.mesh.core

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.ServerSocket
import java.net.Socket
import java.security.KeyStore
import java.security.PrivateKey
import java.security.cert.X509Certificate
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class PairingSession {
    var peerFingerprint: String? = null
    private var sslSocket: SSLSocket? = null

    private fun buildSslContext(identity: Pair<X509Certificate, PrivateKey>): SSLContext {
        val keyStore = KeyStore.getInstance("PKCS12")
        keyStore.load(null, null)
        keyStore.setKeyEntry("mesh", identity.second, charArrayOf(), arrayOf(identity.first))

        val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        kmf.init(keyStore, charArrayOf())

        // Untrusted at handshake stage, per spec — trust is established via the PIN step afterward.
        val trustAllManager = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<out X509Certificate>, authType: String) {}
            override fun checkServerTrusted(chain: Array<out X509Certificate>, authType: String) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        }

        val context = SSLContext.getInstance("TLS")
        context.init(kmf.keyManagers, arrayOf<TrustManager>(trustAllManager), null)
        return context
    }

    suspend fun startListener(identity: Pair<X509Certificate, PrivateKey>, port: Int) {
        withContext(Dispatchers.IO) {
            val context = buildSslContext(identity)
            val factory = context.serverSocketFactory
            val serverSocket = factory.createServerSocket(port) as javax.net.ssl.SSLServerSocket
            serverSocket.needClientAuth = true
            serverSocket.soTimeout = 10_000

            val socket = serverSocket.accept() as SSLSocket
            socket.startHandshake()
            serverSocket.close()

            sslSocket = socket
            val peerCert = socket.session.peerCertificates[0] as X509Certificate
            peerFingerprint = IdentityStore.fingerprint(peerCert)
        }
    }

    suspend fun connectTo(identity: Pair<X509Certificate, PrivateKey>, ip: String, port: Int) {
        withContext(Dispatchers.IO) {
            val context = buildSslContext(identity)
            val factory = context.socketFactory
            val socket = factory.createSocket(ip, port) as SSLSocket
            socket.soTimeout = 10_000
            socket.startHandshake()

            sslSocket = socket
            val peerCert = socket.session.peerCertificates[0] as X509Certificate
            peerFingerprint = IdentityStore.fingerprint(peerCert)
        }
    }

    fun computePin(localCert: X509Certificate): String {
        val fp = peerFingerprint ?: throw IllegalStateException("Handshake has not completed yet.")
        return PinDerivation.derive(IdentityStore.fingerprint(localCert), fp)
    }

    suspend fun isPeerTrusted(dao: PairedDeviceDao, uuid: String): Boolean {
        val record = dao.findByUuid(uuid) ?: return false
        return record.fingerprint == peerFingerprint
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests "com.mesh.core.PairingSessionTest"`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add android
git commit -m "feat(android): TLS pairing session with fingerprint-based PIN and trust check"
```

---

## Task 12: Android UI (device list, PIN confirmation, connect flow)

**Files:**
- Create: `android/app/src/main/java/com/mesh/ui/MainActivity.kt`
- Create: `android/app/src/main/res/layout/activity_main.xml`
- Create: `android/app/src/main/java/com/mesh/ui/PinConfirmDialog.kt`

**Interfaces:**
- Consumes: `com.mesh.core.MeshDiscovery`, `com.mesh.core.PairingSession`, `com.mesh.core.IdentityStore`, `com.mesh.core.MeshDatabase`, `com.mesh.core.PairedDevice`.
- Produces: none consumed by later tasks (UI is a leaf in this sub-project).

- [ ] **Step 1: Write activity_main.xml**

```xml
<!-- android/app/src/main/res/layout/activity_main.xml -->
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:orientation="vertical"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Discovered devices"
        android:textStyle="bold"
        android:layout_marginBottom="8dp"/>

    <ListView
        android:id="@+id/deviceListView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"/>

    <Button
        android:id="@+id/connectButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Connect"/>
</LinearLayout>
```

- [ ] **Step 2: Write PinConfirmDialog.kt**

```kotlin
// android/app/src/main/java/com/mesh/ui/PinConfirmDialog.kt
package com.mesh.ui

import android.app.AlertDialog
import android.content.Context

object PinConfirmDialog {
    fun show(context: Context, pin: String, onResult: (Boolean) -> Unit) {
        AlertDialog.Builder(context)
            .setTitle("Confirm PIN")
            .setMessage("Does this PIN match the other device?\n\n$pin")
            .setPositiveButton("Match") { _, _ -> onResult(true) }
            .setNegativeButton("Not matching") { _, _ -> onResult(false) }
            .setCancelable(false)
            .show()
    }
}
```

- [ ] **Step 3: Write MainActivity.kt wiring discovery, connect, and pairing**

```kotlin
// android/app/src/main/java/com/mesh/ui/MainActivity.kt
package com.mesh.ui

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.mesh.core.*
import kotlinx.coroutines.launch
import java.util.UUID

class MainActivity : AppCompatActivity() {
    private val devices = mutableListOf<DiscoveredDevice>()
    private lateinit var adapter: ArrayAdapter<String>
    private lateinit var discovery: MeshDiscovery

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(com.mesh.R.layout.activity_main)

        val listView = findViewById<ListView>(com.mesh.R.id.deviceListView)
        adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, mutableListOf())
        listView.adapter = adapter

        discovery = MeshDiscovery(this)
        val selfUuid = UUID.randomUUID().toString() // stable per-install id; persisted separately in a future task
        discovery.advertise(selfUuid, android.os.Build.MODEL, "android", 51555)
        discovery.startBrowsing { device ->
            runOnUiThread {
                if (devices.any { it.uuid == device.uuid }) return@runOnUiThread
                devices.add(device)
                adapter.add(device.name)
            }
        }

        var selectedIndex = -1
        listView.setOnItemClickListener { _, _, position, _ -> selectedIndex = position }

        findViewById<android.widget.Button>(com.mesh.R.id.connectButton).setOnClickListener {
            if (selectedIndex < 0) return@setOnClickListener
            connectTo(devices[selectedIndex])
        }
    }

    private fun connectTo(target: DiscoveredDevice) {
        lifecycleScope.launch {
            val identity = IdentityStore.loadOrCreate(this@MainActivity)
            val session = PairingSession()
            try {
                session.connectTo(identity, target.ipAddress, target.port)
            } catch (ex: Exception) {
                Toast.makeText(this@MainActivity, "Connection failed: ${ex.message}", Toast.LENGTH_LONG).show()
                return@launch
            }

            val dao = MeshDatabase.getInstance(this@MainActivity).pairedDeviceDao()
            if (session.isPeerTrusted(dao, target.uuid)) {
                Toast.makeText(this@MainActivity, "Reconnected to ${target.name} (trusted).", Toast.LENGTH_LONG).show()
                return@launch
            }

            val pin = session.computePin(identity.first)
            PinConfirmDialog.show(this@MainActivity, pin) { matched ->
                lifecycleScope.launch {
                    if (!matched) {
                        Toast.makeText(this@MainActivity, "Pairing failed.", Toast.LENGTH_LONG).show()
                        return@launch
                    }
                    dao.upsert(PairedDevice(
                        uuid = target.uuid,
                        name = target.name,
                        fingerprint = session.peerFingerprint!!,
                        lastIp = target.ipAddress,
                        pairedAt = System.currentTimeMillis()
                    ))
                    Toast.makeText(this@MainActivity, "Paired with ${target.name}.", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}
```

- [ ] **Step 4: Build to verify it compiles**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL

- [ ] **Step 5: Commit**

```bash
git add android
git commit -m "feat(android): device list UI with PIN confirmation dialog"
```

---

## Notes for the executor

- Tasks 1–6 (Windows) and 7–12 (Android) are independent of each other and could run in parallel subagent lanes if using subagent-driven-development; within each platform, tasks are sequential (each depends on the Core types from the previous one).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` are excluded by the user's global `~/.config/git/ignore` — this is intentional and already accounted for; do not pass `-f` to force-add them.
- Any mDNS/multicast test that fails purely because the sandbox network blocks multicast should be marked skipped with a one-line reason, not deleted or rewritten to assert something weaker.
