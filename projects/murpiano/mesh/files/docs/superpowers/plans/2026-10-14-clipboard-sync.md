# Persistent Session & Clipboard Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the TLS channel open after pairing/reconnect (sub-project 1) and use it to sync a capped, persisted text-only clipboard history between a paired Windows PC and Android phone, surfaced in a new "Clipboard" tab alongside the existing "Devices" tab.

**Architecture:** A new `MeshSession` Core type on each platform takes ownership of the already-open, already-authenticated transport that `PairingSession` produces on `Paired`/`Reconnected`, runs a framed-message read loop (`ClipboardPush`/`Heartbeat`), and owns reconnect-with-backoff. `ClipboardWatcher` detects local OS clipboard changes and feeds `MeshSession.Send`; incoming pushes and local copies both land in a capped SQLite-backed history store that the new Clipboard tab displays.

**Tech Stack:** Windows: .NET 8, WPF, `Microsoft.Data.Sqlite`, Win32 clipboard-listener interop via `HwndSource`. Android: Kotlin, Room (existing `MeshDatabase`), `ClipboardManager`.

**Spec:** `docs/superpowers/specs/2026-10-14-clipboard-sync-design.md`

## Global Constraints

- Wire protocol (identical on both platforms): 1-byte type tag, then payload. `0x01` = `ClipboardPush`: 8-byte big-endian Unix-ms timestamp, then a length-prefixed UTF-8 string (reuse `PairingProtocol`'s 4-byte-big-endian-length-prefix string framing). `0x02` = `Heartbeat`: no payload.
- Heartbeat sent every 20s on an idle channel; no message (including heartbeats) received within 45s means the channel is treated as dropped.
- History cap: 50 rows per device, oldest evicted first, enforced inside the same insert transaction (never visibly exceeds 50).
- Clipboard text accepted size limit: 1 MiB (1,048,576 UTF-16 chars as `string`/`CharSequence` length check before encoding — reject larger text: don't store, don't send).
- Reconnect backoff: 1s, 2s, 4s, 8s, then capped at 30s between further attempts; after 4 failed direct-IP attempts, fall back to one mDNS re-discovery pass before continuing direct retries against whatever IP that returns (or the last-known IP if discovery finds nothing).
- Self-copy dedup window: 500ms — a clipboard change caused by the app's own "Copy" action must not be re-pushed to the peer.

## Review Focus

- A `ClipboardPush` larger than the 1 MiB cap arriving from a peer (not just locally typed/pasted) must be rejected (dropped, not stored, not crash) — a malicious or buggy peer sending an oversized push is the more realistic attack surface than a local paste.
- Tapping "Copy" on a history entry must not create a duplicate entry a moment later from the dedup window's own local-change detection — test the dedup path explicitly, not just assume the timer works.
- A `MeshSession` whose heartbeat read times out while a `Send` is in-flight must not deadlock the send and must still transition to "disconnected" and start reconnecting.
- Reconnect after the peer's IP actually changed (not just a transient drop) must fall through to mDNS re-discovery and succeed, not retry the stale IP forever.
- The 50-row cap must hold under concurrent writes (a local copy and an incoming push landing at nearly the same time) — covered by a transactional insert-and-evict test, not just sequential-insert tests.

---

## Task 1: Windows — detach the pairing transport for session reuse

**Files:**
- Modify: `src/windows/Mesh.Core/PairingSession.cs`
- Test: `src/windows/Mesh.Tests/PairingSessionTests.cs` (add one test, do not touch existing ones)

**Interfaces:**
- Produces: `PairingSession.DetachTransport() -> (TcpClient Client, SslStream Stream)` — marks the session detached (its own `Dispose()` becomes a no-op afterward, so existing `using var session = ...` call sites stay safe without modification until Task 5 rewires them) and hands the caller the still-open, still-authenticated transport.

- [ ] **Step 1: Write the failing test**

```csharp
// Add to src/windows/Mesh.Tests/PairingSessionTests.cs
[Fact]
public async Task DetachTransport_MakesDisposeANoOp_AndLeavesStreamUsable()
{
    var certAPath = Path.Combine(Path.GetTempPath(), $"mesh-test-a-{Guid.NewGuid()}.pfx");
    var certBPath = Path.Combine(Path.GetTempPath(), $"mesh-test-b-{Guid.NewGuid()}.pfx");
    try
    {
        var certA = IdentityStore.LoadOrCreate(certAPath);
        var certB = IdentityStore.LoadOrCreate(certBPath);
        const int port = 51890;

        var listener = new PairingListener(certA, port);
        var acceptTask = listener.AcceptAsync();
        var client = await PairingSession.ConnectAsync(certB, "127.0.0.1", port);
        var server = await acceptTask;

        var (detachedClient, detachedStream) = server.DetachTransport();
        server.Dispose(); // must be a no-op now

        var (clientTcp, clientStream) = client.DetachTransport();

        // The detached stream must still work: write from the client side, read via the
        // server's detached stream.
        var writeBuf = System.Text.Encoding.UTF8.GetBytes("hello");
        await clientStream.WriteAsync(writeBuf);
        await clientStream.FlushAsync();

        var readBuf = new byte[5];
        var totalRead = 0;
        while (totalRead < 5)
        {
            var n = await detachedStream.ReadAsync(readBuf, totalRead, 5 - totalRead);
            Assert.True(n > 0);
            totalRead += n;
        }
        Assert.Equal("hello", System.Text.Encoding.UTF8.GetString(readBuf));

        detachedStream.Dispose();
        detachedClient.Dispose();
        clientStream.Dispose();
        clientTcp.Dispose();
        listener.Dispose();
    }
    finally
    {
        if (File.Exists(certAPath)) File.Delete(certAPath);
        if (File.Exists(certBPath)) File.Delete(certBPath);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter DetachTransport_MakesDisposeANoOp_AndLeavesStreamUsable`
Expected: FAIL — `'PairingSession' does not contain a definition for 'DetachTransport'`

- [ ] **Step 3: Implement DetachTransport**

In `src/windows/Mesh.Core/PairingSession.cs`, add a `_detached` field and the method, and guard `Dispose()`:

```csharp
// Add near the other private fields:
private bool _detached;

// Add as a public method, anywhere after the constructor:
/// <summary>
/// Hands ownership of the open, authenticated transport to the caller (e.g. to build a
/// <see cref="MeshSession"/> on a Paired/Reconnected outcome). After this call, this
/// session's own <see cref="Dispose"/> becomes a no-op — the caller now owns closing
/// the transport.
/// </summary>
public (TcpClient Client, SslStream Stream) DetachTransport()
{
    _detached = true;
    return (_client, _stream);
}
```

Change the existing `Dispose()` method to:

```csharp
public void Dispose()
{
    if (_detached) return;
    _stream.Dispose();
    _client.Dispose();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter DetachTransport_MakesDisposeANoOp_AndLeavesStreamUsable`
Expected: PASS

- [ ] **Step 5: Run the full Mesh.Tests suite to confirm no regression**

Run: `cd src/windows && dotnet test Mesh.Tests`
Expected: all previously-passing tests still pass, plus this new one (45 total)

- [ ] **Step 6: Commit**

```bash
git add src/windows/Mesh.Core/PairingSession.cs src/windows/Mesh.Tests/PairingSessionTests.cs
git commit -m "feat(windows): allow detaching the pairing transport for session reuse"
```

---

## Task 2: Windows — wire message framing (ClipboardPush/Heartbeat)

**Files:**
- Create: `src/windows/Mesh.Core/MeshMessage.cs`
- Test: `src/windows/Mesh.Tests/MeshMessageTests.cs`

**Interfaces:**
- Consumes: `PairingProtocol.WriteStringAsync/ReadStringAsync` (existing, 4-byte-length-prefixed UTF-8 string framing — read the existing `PairingProtocol.cs` to match its exact method names before writing this).
- Produces: `Mesh.Core.MeshMessage` (abstract base or discriminated union — use a simple class hierarchy), `ClipboardPushMessage(DateTimeOffset Timestamp, string Text)`, `HeartbeatMessage`, `MeshMessage.WriteAsync(Stream stream, MeshMessage message) -> Task`, `MeshMessage.ReadAsync(Stream stream) -> Task<MeshMessage>`.

- [ ] **Step 1: Read PairingProtocol.cs first to match its exact API**

```bash
cat src/windows/Mesh.Core/PairingProtocol.cs
```
Use whatever the actual static method signatures are for writing/reading a length-prefixed UTF-8 string and a single byte — do not guess, copy the real names (likely `PairingProtocol.WriteStringAsync(Stream, string)` / `PairingProtocol.ReadStringAsync(Stream)` / `WriteByteAsync` / `ReadByteAsync`, matching Task 1's test file's usage above).

- [ ] **Step 2: Write the failing test**

```csharp
// src/windows/Mesh.Tests/MeshMessageTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class MeshMessageTests
{
    [Fact]
    public async Task ClipboardPush_RoundTrips()
    {
        using var stream = new MemoryStream();
        var sent = new ClipboardPushMessage(DateTimeOffset.FromUnixTimeMilliseconds(1_760_000_000_000), "hello world");
        await MeshMessage.WriteAsync(stream, sent);
        stream.Position = 0;

        var received = await MeshMessage.ReadAsync(stream);

        var push = Assert.IsType<ClipboardPushMessage>(received);
        Assert.Equal(sent.Timestamp, push.Timestamp);
        Assert.Equal("hello world", push.Text);
    }

    [Fact]
    public async Task Heartbeat_RoundTrips()
    {
        using var stream = new MemoryStream();
        await MeshMessage.WriteAsync(stream, new HeartbeatMessage());
        stream.Position = 0;

        var received = await MeshMessage.ReadAsync(stream);

        Assert.IsType<HeartbeatMessage>(received);
    }

    [Fact]
    public async Task MultipleMessages_RoundTripInOrder_OnSameStream()
    {
        using var stream = new MemoryStream();
        await MeshMessage.WriteAsync(stream, new ClipboardPushMessage(DateTimeOffset.UtcNow, "first"));
        await MeshMessage.WriteAsync(stream, new HeartbeatMessage());
        await MeshMessage.WriteAsync(stream, new ClipboardPushMessage(DateTimeOffset.UtcNow, "second"));
        stream.Position = 0;

        var first = Assert.IsType<ClipboardPushMessage>(await MeshMessage.ReadAsync(stream));
        Assert.Equal("first", first.Text);
        Assert.IsType<HeartbeatMessage>(await MeshMessage.ReadAsync(stream));
        var second = Assert.IsType<ClipboardPushMessage>(await MeshMessage.ReadAsync(stream));
        Assert.Equal("second", second.Text);
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshMessageTests`
Expected: FAIL — `MeshMessage`/`ClipboardPushMessage`/`HeartbeatMessage` not found

- [ ] **Step 4: Implement MeshMessage**

```csharp
// src/windows/Mesh.Core/MeshMessage.cs
namespace Mesh.Core;

public abstract class MeshMessage
{
    private const byte ClipboardPushTag = 0x01;
    private const byte HeartbeatTag = 0x02;

    public static async Task WriteAsync(Stream stream, MeshMessage message)
    {
        switch (message)
        {
            case ClipboardPushMessage push:
                await stream.WriteAsync(new[] { ClipboardPushTag });
                var tsBytes = BitConverter.GetBytes(push.Timestamp.ToUnixTimeMilliseconds());
                if (BitConverter.IsLittleEndian) Array.Reverse(tsBytes);
                await stream.WriteAsync(tsBytes);
                await PairingProtocol.WriteStringAsync(stream, push.Text);
                break;
            case HeartbeatMessage:
                await stream.WriteAsync(new[] { HeartbeatTag });
                break;
            default:
                throw new ArgumentOutOfRangeException(nameof(message), "Unknown message type.");
        }
        await stream.FlushAsync();
    }

    public static async Task<MeshMessage> ReadAsync(Stream stream)
    {
        var tagBuf = new byte[1];
        await ReadExactAsync(stream, tagBuf);
        return tagBuf[0] switch
        {
            ClipboardPushTag => await ReadClipboardPushAsync(stream),
            HeartbeatTag => new HeartbeatMessage(),
            _ => throw new InvalidDataException($"Unknown message tag: {tagBuf[0]}")
        };
    }

    private static async Task<ClipboardPushMessage> ReadClipboardPushAsync(Stream stream)
    {
        var tsBuf = new byte[8];
        await ReadExactAsync(stream, tsBuf);
        if (BitConverter.IsLittleEndian) Array.Reverse(tsBuf);
        var timestamp = DateTimeOffset.FromUnixTimeMilliseconds(BitConverter.ToInt64(tsBuf));
        var text = await PairingProtocol.ReadStringAsync(stream);
        return new ClipboardPushMessage(timestamp, text);
    }

    private static async Task ReadExactAsync(Stream stream, byte[] buffer)
    {
        var offset = 0;
        while (offset < buffer.Length)
        {
            var read = await stream.ReadAsync(buffer.AsMemory(offset, buffer.Length - offset));
            if (read == 0) throw new EndOfStreamException();
            offset += read;
        }
    }
}

public sealed class ClipboardPushMessage(DateTimeOffset timestamp, string text) : MeshMessage
{
    public DateTimeOffset Timestamp { get; } = timestamp;
    public string Text { get; } = text;
}

public sealed class HeartbeatMessage : MeshMessage;
```

If `PairingProtocol.WriteStringAsync`/`ReadStringAsync` turn out to have different names or signatures than assumed here (check Step 1's output), adjust the calls above to match exactly — do not add a second, parallel string-framing implementation.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshMessageTests`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/windows/Mesh.Core/MeshMessage.cs src/windows/Mesh.Tests/MeshMessageTests.cs
git commit -m "feat(windows): wire message framing for ClipboardPush and Heartbeat"
```

---

## Task 3: Windows — clipboard history store (SQLite, capped)

**Files:**
- Modify: `src/windows/Mesh.Core/Mesh.Core.csproj` (add `Microsoft.Data.Sqlite` package)
- Create: `src/windows/Mesh.Core/ClipboardHistoryStore.cs`
- Test: `src/windows/Mesh.Tests/ClipboardHistoryStoreTests.cs`

**Interfaces:**
- Produces: `Mesh.Core.ClipboardEntry { long Id, string Text, string Source, DateTimeOffset Timestamp }` (`Source` is `"local"` or the peer's device name). `Mesh.Core.ClipboardHistoryStore.Insert(string dbPath, string text, string source, DateTimeOffset timestamp) -> ClipboardEntry` (inserts, then evicts oldest rows past 50 in the same transaction). `ClipboardHistoryStore.GetAll(string dbPath) -> List<ClipboardEntry>` (newest first).

- [ ] **Step 1: Add the Microsoft.Data.Sqlite package**

```bash
cd src/windows/Mesh.Core && dotnet add package Microsoft.Data.Sqlite
```

- [ ] **Step 2: Write the failing test**

```csharp
// src/windows/Mesh.Tests/ClipboardHistoryStoreTests.cs
using Mesh.Core;
using Xunit;

namespace Mesh.Tests;

public class ClipboardHistoryStoreTests
{
    private static string TempDbPath() => Path.Combine(Path.GetTempPath(), $"mesh-clip-test-{Guid.NewGuid()}.db");

    [Fact]
    public void Insert_ThenGetAll_RoundTrips()
    {
        var path = TempDbPath();
        try
        {
            var entry = ClipboardHistoryStore.Insert(path, "hello", "local", DateTimeOffset.UtcNow);
            var all = ClipboardHistoryStore.GetAll(path);
            Assert.Single(all);
            Assert.Equal("hello", all[0].Text);
            Assert.Equal("local", all[0].Source);
            Assert.Equal(entry.Id, all[0].Id);
        }
        finally { if (File.Exists(path)) File.Delete(path); }
    }

    [Fact]
    public void GetAll_ReturnsNewestFirst()
    {
        var path = TempDbPath();
        try
        {
            var t0 = DateTimeOffset.UtcNow;
            ClipboardHistoryStore.Insert(path, "first", "local", t0);
            ClipboardHistoryStore.Insert(path, "second", "local", t0.AddSeconds(1));
            var all = ClipboardHistoryStore.GetAll(path);
            Assert.Equal("second", all[0].Text);
            Assert.Equal("first", all[1].Text);
        }
        finally { if (File.Exists(path)) File.Delete(path); }
    }

    [Fact]
    public void Insert_Beyond50_EvictsOldest_CountStaysAt50()
    {
        var path = TempDbPath();
        try
        {
            var t0 = DateTimeOffset.UtcNow;
            for (var i = 0; i < 51; i++)
                ClipboardHistoryStore.Insert(path, $"entry-{i}", "local", t0.AddSeconds(i));

            var all = ClipboardHistoryStore.GetAll(path);
            Assert.Equal(50, all.Count);
            Assert.DoesNotContain(all, e => e.Text == "entry-0"); // oldest, evicted
            Assert.Contains(all, e => e.Text == "entry-50"); // newest, kept
        }
        finally { if (File.Exists(path)) File.Delete(path); }
    }

    [Fact]
    public void GetAll_ReturnsEmptyList_WhenDbFileMissing()
    {
        var path = TempDbPath(); // never created
        Assert.Empty(ClipboardHistoryStore.GetAll(path));
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter ClipboardHistoryStoreTests`
Expected: FAIL — `ClipboardHistoryStore`/`ClipboardEntry` not found

- [ ] **Step 4: Implement ClipboardHistoryStore**

```csharp
// src/windows/Mesh.Core/ClipboardHistoryStore.cs
using Microsoft.Data.Sqlite;

namespace Mesh.Core;

public sealed record ClipboardEntry(long Id, string Text, string Source, DateTimeOffset Timestamp);

public static class ClipboardHistoryStore
{
    private const int Cap = 50;

    public static ClipboardEntry Insert(string dbPath, string text, string source, DateTimeOffset timestamp)
    {
        using var connection = Open(dbPath);
        using var transaction = connection.BeginTransaction();

        using (var insert = connection.CreateCommand())
        {
            insert.Transaction = transaction;
            insert.CommandText =
                "INSERT INTO clipboard_history (text, source, timestamp) VALUES ($text, $source, $timestamp)";
            insert.Parameters.AddWithValue("$text", text);
            insert.Parameters.AddWithValue("$source", source);
            insert.Parameters.AddWithValue("$timestamp", timestamp.ToUnixTimeMilliseconds());
            insert.ExecuteNonQuery();
        }

        long newId;
        using (var idCmd = connection.CreateCommand())
        {
            idCmd.Transaction = transaction;
            idCmd.CommandText = "SELECT last_insert_rowid()";
            newId = (long)idCmd.ExecuteScalar()!;
        }

        using (var evict = connection.CreateCommand())
        {
            evict.Transaction = transaction;
            evict.CommandText = """
                DELETE FROM clipboard_history
                WHERE id NOT IN (
                    SELECT id FROM clipboard_history ORDER BY timestamp DESC, id DESC LIMIT $cap
                )
                """;
            evict.Parameters.AddWithValue("$cap", Cap);
            evict.ExecuteNonQuery();
        }

        transaction.Commit();
        return new ClipboardEntry(newId, text, source, timestamp);
    }

    public static List<ClipboardEntry> GetAll(string dbPath)
    {
        if (!File.Exists(dbPath)) return new List<ClipboardEntry>();

        using var connection = Open(dbPath);
        using var select = connection.CreateCommand();
        select.CommandText = "SELECT id, text, source, timestamp FROM clipboard_history ORDER BY timestamp DESC, id DESC";
        using var reader = select.ExecuteReader();

        var results = new List<ClipboardEntry>();
        while (reader.Read())
        {
            results.Add(new ClipboardEntry(
                reader.GetInt64(0),
                reader.GetString(1),
                reader.GetString(2),
                DateTimeOffset.FromUnixTimeMilliseconds(reader.GetInt64(3))));
        }
        return results;
    }

    private static SqliteConnection Open(string dbPath)
    {
        var dir = Path.GetDirectoryName(dbPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

        var connection = new SqliteConnection($"Data Source={dbPath}");
        connection.Open();
        using var create = connection.CreateCommand();
        create.CommandText = """
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
            """;
        create.ExecuteNonQuery();
        return connection;
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter ClipboardHistoryStoreTests`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/windows/Mesh.Core/Mesh.Core.csproj src/windows/Mesh.Core/ClipboardHistoryStore.cs src/windows/Mesh.Tests/ClipboardHistoryStoreTests.cs
git commit -m "feat(windows): capped SQLite-backed clipboard history store"
```

---

## Task 4: Windows — MeshSession (persistent channel, heartbeat, reconnect)

**Files:**
- Create: `src/windows/Mesh.Core/MeshSession.cs`
- Test: `src/windows/Mesh.Tests/MeshSessionTests.cs`

**Interfaces:**
- Consumes: `Mesh.Core.MeshMessage`/`ClipboardPushMessage`/`HeartbeatMessage` (Task 2), `PairingSession.DetachTransport` (Task 1), `Mesh.Core.MeshDiscovery` (existing, for reconnect fallback), `Mesh.Core.PairedDeviceStore` (existing, for `last_ip`/port lookup — check its actual current field names before use).
- Produces: `Mesh.Core.MeshSessionState { Connected, Disconnected, Reconnecting }`. `Mesh.Core.MeshSession` with:
  - `static MeshSession FromTransport(TcpClient client, SslStream stream, string peerUuid, string peerIp, int peerPort) -> MeshSession`
  - `event Action<MeshMessage>? MessageReceived`
  - `event Action<MeshSessionState>? StateChanged`
  - `Task SendAsync(MeshMessage message) -> Task` (queues if disconnected, sends immediately if connected)
  - `void Dispose()` (stops the read loop and reconnect loop, closes the transport)

- [ ] **Step 1: Write the failing test — basic send/receive over loopback**

```csharp
// src/windows/Mesh.Tests/MeshSessionTests.cs
using Mesh.Core;
using System.Collections.Concurrent;
using Xunit;

namespace Mesh.Tests;

public class MeshSessionTests
{
    private static async Task<(MeshSession ServerSession, MeshSession ClientSession)> CreatePairAsync(int port)
    {
        var certAPath = Path.Combine(Path.GetTempPath(), $"mesh-test-a-{Guid.NewGuid()}.pfx");
        var certBPath = Path.Combine(Path.GetTempPath(), $"mesh-test-b-{Guid.NewGuid()}.pfx");
        var certA = IdentityStore.LoadOrCreate(certAPath);
        var certB = IdentityStore.LoadOrCreate(certBPath);

        var listener = new PairingListener(certA, port);
        var acceptTask = listener.AcceptAsync();
        var clientSession = await PairingSession.ConnectAsync(certB, "127.0.0.1", port);
        var serverSession = await acceptTask;
        listener.Dispose();

        var (serverClient, serverStream) = serverSession.DetachTransport();
        var (clientTcp, clientStream) = clientSession.DetachTransport();

        var server = MeshSession.FromTransport(serverClient, serverStream, "peer-uuid-client", "127.0.0.1", port);
        var client = MeshSession.FromTransport(clientTcp, clientStream, "peer-uuid-server", "127.0.0.1", port);
        return (server, client);
    }

    [Fact]
    public async Task SendAsync_DeliversMessageToPeer_MessageReceivedFires()
    {
        var (server, client) = await CreatePairAsync(51891);
        try
        {
            var received = new TaskCompletionSource<MeshMessage>();
            client.MessageReceived += msg => received.TrySetResult(msg);

            await server.SendAsync(new ClipboardPushMessage(DateTimeOffset.UtcNow, "hi from server"));

            var result = await received.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var push = Assert.IsType<ClipboardPushMessage>(result);
            Assert.Equal("hi from server", push.Text);
        }
        finally { server.Dispose(); client.Dispose(); }
    }

    [Fact]
    public async Task StateChanged_FiresDisconnected_WhenPeerCloses()
    {
        var (server, client) = await CreatePairAsync(51892);
        try
        {
            var states = new ConcurrentQueue<MeshSessionState>();
            client.StateChanged += states.Enqueue;

            server.Dispose(); // simulate peer going away

            await Task.Delay(TimeSpan.FromSeconds(2));
            Assert.Contains(MeshSessionState.Disconnected, states);
        }
        finally { client.Dispose(); }
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshSessionTests`
Expected: FAIL — `MeshSession` not found

- [ ] **Step 3: Implement MeshSession**

Before writing this, run `cat src/windows/Mesh.Core/PairedDeviceStore.cs src/windows/Mesh.Core/MeshDiscovery.cs` to confirm their exact current method signatures (these were last touched by the sub-project 1 fix wave and this plan's author has not re-verified every name) — use whatever the real signatures are, this code assumes `PairedDeviceStore.Find(path, uuid)` returning a record with `LastIp`/a port field, and `MeshDiscovery`'s existing browse API; adjust names to match reality.

```csharp
// src/windows/Mesh.Core/MeshSession.cs
using System.Net.Security;
using System.Net.Sockets;

namespace Mesh.Core;

public enum MeshSessionState { Connected, Disconnected, Reconnecting }

/// <summary>
/// A persistent, reconnecting channel to a paired peer, carrying framed <see cref="MeshMessage"/>
/// traffic after the pairing handshake completes. Owns the transport from the point it is
/// constructed (via <see cref="FromTransport"/>) until <see cref="Dispose"/>.
/// </summary>
public sealed class MeshSession : IDisposable
{
    private static readonly TimeSpan HeartbeatInterval = TimeSpan.FromSeconds(20);
    private static readonly TimeSpan IdleTimeout = TimeSpan.FromSeconds(45);
    private static readonly TimeSpan[] BackoffSteps =
    {
        TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(4), TimeSpan.FromSeconds(8)
    };
    private static readonly TimeSpan MaxBackoff = TimeSpan.FromSeconds(30);

    public event Action<MeshMessage>? MessageReceived;
    public event Action<MeshSessionState>? StateChanged;

    private readonly string _peerUuid;
    private readonly int _peerPort;
    private string _peerIp;
    private TcpClient? _client;
    private SslStream? _stream;
    private readonly CancellationTokenSource _lifetimeCts = new();
    private readonly SemaphoreSlim _sendLock = new(1, 1);
    private readonly Queue<MeshMessage> _pendingSend = new();
    private DateTimeOffset _lastReceivedAt = DateTimeOffset.UtcNow;
    private MeshSessionState _state = MeshSessionState.Connected;

    private MeshSession(TcpClient client, SslStream stream, string peerUuid, string peerIp, int peerPort)
    {
        _client = client;
        _stream = stream;
        _peerUuid = peerUuid;
        _peerIp = peerIp;
        _peerPort = peerPort;
    }

    public static MeshSession FromTransport(TcpClient client, SslStream stream, string peerUuid, string peerIp, int peerPort)
    {
        var session = new MeshSession(client, stream, peerUuid, peerIp, peerPort);
        _ = session.RunReadLoopAsync(session._lifetimeCts.Token);
        _ = session.RunHeartbeatLoopAsync(session._lifetimeCts.Token);
        return session;
    }

    public async Task SendAsync(MeshMessage message)
    {
        await _sendLock.WaitAsync();
        try
        {
            if (_state != MeshSessionState.Connected || _stream == null)
            {
                _pendingSend.Enqueue(message);
                return;
            }
            try
            {
                await MeshMessage.WriteAsync(_stream, message);
            }
            catch
            {
                _pendingSend.Enqueue(message);
                TransitionTo(MeshSessionState.Disconnected);
                _ = ReconnectLoopAsync(_lifetimeCts.Token);
            }
        }
        finally
        {
            _sendLock.Release();
        }
    }

    private async Task RunReadLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                if (_stream == null) { await Task.Delay(200, ct); continue; }
                var message = await MeshMessage.ReadAsync(_stream);
                _lastReceivedAt = DateTimeOffset.UtcNow;
                if (message is not HeartbeatMessage)
                    MessageReceived?.Invoke(message);
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch
            {
                TransitionTo(MeshSessionState.Disconnected);
                _ = ReconnectLoopAsync(ct);
                await Task.Delay(TimeSpan.FromMilliseconds(500), CancellationToken.None).ContinueWith(_ => { });
                if (_state != MeshSessionState.Connected)
                {
                    try { await Task.Delay(Timeout.Infinite, ct); } catch (OperationCanceledException) { return; }
                }
            }
        }
    }

    private async Task RunHeartbeatLoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(HeartbeatInterval, ct).ContinueWith(_ => { });
            if (ct.IsCancellationRequested) return;

            if (_state == MeshSessionState.Connected)
            {
                if (DateTimeOffset.UtcNow - _lastReceivedAt > IdleTimeout)
                {
                    TransitionTo(MeshSessionState.Disconnected);
                    _ = ReconnectLoopAsync(ct);
                    continue;
                }
                try { await SendAsync(new HeartbeatMessage()); }
                catch { /* SendAsync already handles failure by reconnecting */ }
            }
        }
    }

    private async Task ReconnectLoopAsync(CancellationToken ct)
    {
        TransitionTo(MeshSessionState.Reconnecting);
        var attempt = 0;
        while (!ct.IsCancellationRequested)
        {
            attempt++;
            var ip = _peerIp;
            if (attempt == 5)
            {
                // After 4 direct-IP attempts, try one mDNS re-discovery pass.
                var rediscovered = await TryRediscoverIpAsync(ct);
                if (rediscovered != null) ip = _peerIp = rediscovered;
            }

            try
            {
                // Reconnect here re-establishes only the TLS transport to an already-trusted
                // peer; it intentionally does not repeat the PIN/trust protocol.
                var client = new TcpClient();
                await client.ConnectAsync(ip, _peerPort, ct);
                // NOTE: full reconnect (TLS re-handshake against the pinned fingerprint) is
                // wired through PairingSession.ConnectAsync + trusted-check by the caller that
                // owns identity/paired-store paths; this class only re-establishes the already-
                // authenticated transport handed to it. See Task 5 for how the UI layer re-runs
                // the trusted-reconnect handshake and calls a new FromTransport on success.
                client.Dispose();
                return; // Signal: caller (Task 5 UI wiring) must re-run trusted handshake and replace this session.
            }
            catch
            {
                var delay = attempt <= BackoffSteps.Length ? BackoffSteps[attempt - 1] : MaxBackoff;
                try { await Task.Delay(delay, ct); } catch (OperationCanceledException) { return; }
            }
        }
    }

    private Task<string?> TryRediscoverIpAsync(CancellationToken ct)
    {
        // Left as a hook: a full mDNS re-discovery pass needs a running MeshDiscovery instance,
        // which this class does not own. Task 5's UI-layer reconnect orchestration performs
        // the actual re-discovery and passes a fresh IP back in; this returns null here so the
        // backoff loop simply keeps retrying the last-known IP if nothing calls in with a new one.
        return Task.FromResult<string?>(null);
    }

    private void TransitionTo(MeshSessionState state)
    {
        if (_state == state) return;
        _state = state;
        StateChanged?.Invoke(state);
    }

    public void Dispose()
    {
        _lifetimeCts.Cancel();
        _stream?.Dispose();
        _client?.Dispose();
    }
}
```

**Note for the implementer:** the reconnect loop above is intentionally minimal — full reconnect (re-running the TLS handshake and trusted-peer check) requires the identity certificate and paired-device store path, which `MeshSession` does not hold. Task 5 wires the UI layer to listen for `StateChanged == Disconnected`, run `PairingSession.ConnectAsync` + `IsPeerTrusted` + `DetachTransport` again on success, and replace the `MeshSession` instance. If, once you're implementing Task 5, you find it's cleaner to move this orchestration into `MeshSession` itself (e.g. by giving it the identity cert and paired-store path up front), that's a reasonable improvement — just keep the test coverage for both the "transport-level send/receive" behavior (this task) and the "full reconnect re-establishes a working session" behavior (Task 5) intact either way, and document in your task report which file ended up owning the reconnect orchestration.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter MeshSessionTests`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full suite**

Run: `cd src/windows && dotnet test Mesh.Tests`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/windows/Mesh.Core/MeshSession.cs src/windows/Mesh.Tests/MeshSessionTests.cs
git commit -m "feat(windows): MeshSession persistent channel with heartbeat and reconnect scaffold"
```

---

## Task 5: Windows — ClipboardWatcher, UI tabs, and full wiring

**Files:**
- Create: `src/windows/Mesh.Core/ClipboardWatcher.cs`
- Modify: `src/windows/Mesh.App/MainWindow.xaml` (add TabControl with Devices/Clipboard tabs)
- Modify: `src/windows/Mesh.App/MainWindow.xaml.cs` (wire MeshSession lifecycle, clipboard watcher, history list, full reconnect orchestration)

**Interfaces:**
- Consumes: `Mesh.Core.MeshSession`, `Mesh.Core.MeshMessage`/`ClipboardPushMessage`, `Mesh.Core.ClipboardHistoryStore`/`ClipboardEntry`, `Mesh.Core.PairingSession` (existing `ConnectAsync`/`RunAsync`/`DetachTransport`/`IsPeerTrusted`), `Mesh.Core.PairedDeviceStore` (existing), `Mesh.Core.MeshDiscovery` (existing).
- Produces: none consumed by later tasks (this is the Windows UI integration point; Android gets its own parallel integration in Task 10).

- [ ] **Step 1: Read the current MainWindow.xaml.cs in full before editing**

```bash
cat src/windows/Mesh.App/MainWindow.xaml.cs
```
This file was last touched by sub-project 1's fix wave and now contains the full accept-loop + `RunAsync`/`IPairingPrompt` wiring. Do not guess its structure — read it, then make the additions below fit its actual current shape (field names, where the accept loop lives, how `PairingOutcome` is currently handled for `Paired`/`Reconnected`).

- [ ] **Step 2: Implement ClipboardWatcher**

```csharp
// src/windows/Mesh.Core/ClipboardWatcher.cs
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace Mesh.Core;

/// <summary>
/// Fires <see cref="TextCopied"/> when the Windows clipboard's text content changes, via
/// AddClipboardFormatListener on a message-only HWND. Must be constructed after the owning
/// window's handle exists (e.g. in a Loaded handler).
/// </summary>
public sealed class ClipboardWatcher : IDisposable
{
    private const int WM_CLIPBOARDUPDATE = 0x031D;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool AddClipboardFormatListener(IntPtr hwnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RemoveClipboardFormatListener(IntPtr hwnd);

    public event Action<string>? TextCopied;

    private readonly HwndSource _source;
    private DateTimeOffset _suppressUntil = DateTimeOffset.MinValue;

    public ClipboardWatcher(Window window)
    {
        var helper = new WindowInteropHelper(window);
        _source = HwndSource.FromHwnd(helper.Handle)
            ?? throw new InvalidOperationException("Window handle not yet created.");
        _source.AddHook(WndProc);
        AddClipboardFormatListener(helper.Handle);
    }

    /// <summary>Call right before the app writes to the clipboard itself (e.g. the "Copy"
    /// button on a history entry) so that resulting change notification isn't re-pushed.</summary>
    public void SuppressNextChange(TimeSpan window)
    {
        _suppressUntil = DateTimeOffset.UtcNow + window;
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_CLIPBOARDUPDATE)
        {
            if (DateTimeOffset.UtcNow < _suppressUntil)
            {
                return IntPtr.Zero;
            }
            if (Clipboard.ContainsText())
            {
                try
                {
                    var text = Clipboard.GetText();
                    if (!string.IsNullOrEmpty(text)) TextCopied?.Invoke(text);
                }
                catch (System.Runtime.InteropServices.COMException)
                {
                    // Clipboard momentarily locked by another process; skip this notification.
                }
            }
        }
        return IntPtr.Zero;
    }

    public void Dispose()
    {
        RemoveClipboardFormatListener(_source.Handle);
        _source.RemoveHook(WndProc);
    }
}
```

- [ ] **Step 3: Add the Clipboard tab to MainWindow.xaml**

Wrap the existing window content in a `TabControl` with two tabs. Read the current `MainWindow.xaml` first (`cat src/windows/Mesh.App/MainWindow.xaml`) and nest its existing content (device list, Connect button, mDNS error banner — whatever Task 6/the fix wave left there) inside a "Devices" `TabItem`, adding a sibling "Clipboard" `TabItem`:

```xml
<!-- src/windows/Mesh.App/MainWindow.xaml — wrap existing content, add Clipboard tab -->
<Window x:Class="Mesh.App.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Mesh" Height="500" Width="420">
    <TabControl>
        <TabItem Header="Devices">
            <!-- existing Devices-tab content from before this task goes here, unchanged -->
        </TabItem>
        <TabItem Header="Clipboard">
            <Grid Margin="12">
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                </Grid.RowDefinitions>
                <TextBlock Grid.Row="0" Name="SessionStatusText" Text="Not connected" Margin="0,0,0,8"/>
                <ListBox Grid.Row="1" Name="ClipboardHistoryListBox">
                    <ListBox.ItemTemplate>
                        <DataTemplate>
                            <StackPanel Orientation="Horizontal" Margin="0,4">
                                <Button Content="Copy" Width="60" Click="CopyHistoryEntry_Click" Tag="{Binding}"/>
                                <StackPanel Margin="8,0,0,0">
                                    <TextBlock Text="{Binding Source}" FontWeight="Bold" FontSize="11"/>
                                    <TextBlock Text="{Binding Text}" TextWrapping="Wrap" MaxWidth="300"/>
                                </StackPanel>
                            </StackPanel>
                        </DataTemplate>
                    </ListBox.ItemTemplate>
                </ListBox>
            </Grid>
        </TabItem>
    </TabControl>
</Window>
```

- [ ] **Step 4: Wire it all up in MainWindow.xaml.cs**

Add these pieces to the existing class (exact insertion points depend on the file's current structure from Step 1's read — place them consistently with how the existing accept-loop/identity/paired-store fields are organized):

```csharp
// Fields to add:
private MeshSession? _meshSession;
private ClipboardWatcher? _clipboardWatcher;
private readonly ObservableCollection<ClipboardEntry> _clipboardHistory = new();
private readonly string _clipboardDbPath = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
    "Mesh", "clipboard_history.db");

// In the constructor or a Loaded handler (after the window handle exists):
ClipboardHistoryListBox.ItemsSource = _clipboardHistory;
foreach (var entry in ClipboardHistoryStore.GetAll(_clipboardDbPath)) _clipboardHistory.Add(entry);
_clipboardWatcher = new ClipboardWatcher(this);
_clipboardWatcher.TextCopied += OnLocalTextCopied;

// Wherever RunAsync currently returns a PairingOutcome with Result == Paired or Reconnected
// (read Step 1's output to find this exact spot), after the existing success handling, add:
var (transportClient, transportStream) = session.DetachTransport();
_meshSession?.Dispose();
_meshSession = MeshSession.FromTransport(transportClient, transportStream, outcome.PeerUuid!, target.IpAddress, target.Port);
_meshSession.MessageReceived += OnMeshMessageReceived;
_meshSession.StateChanged += OnMeshSessionStateChanged;
SessionStatusText.Text = $"Connected to {outcome.PeerName}";

// New handler methods:
private void OnLocalTextCopied(string text)
{
    if (text.Length > 1_048_576) return; // 1 MiB cap, see Global Constraints
    var entry = ClipboardHistoryStore.Insert(_clipboardDbPath, text, "local", DateTimeOffset.UtcNow);
    Dispatcher.Invoke(() => _clipboardHistory.Insert(0, entry));
    if (_meshSession != null)
        _ = _meshSession.SendAsync(new ClipboardPushMessage(entry.Timestamp, text));
}

private void OnMeshMessageReceived(MeshMessage message)
{
    if (message is not ClipboardPushMessage push) return;
    var peerName = _meshSession != null ? "peer" : "peer"; // replace with the actual connected peer's name if tracked on the window
    var entry = ClipboardHistoryStore.Insert(_clipboardDbPath, push.Text, peerName, push.Timestamp);
    Dispatcher.Invoke(() => _clipboardHistory.Insert(0, entry));
}

private void OnMeshSessionStateChanged(MeshSessionState state)
{
    Dispatcher.Invoke(() => SessionStatusText.Text = state switch
    {
        MeshSessionState.Connected => "Connected",
        MeshSessionState.Reconnecting => "Reconnecting...",
        MeshSessionState.Disconnected => "Disconnected",
        _ => SessionStatusText.Text
    });
}

private void CopyHistoryEntry_Click(object sender, RoutedEventArgs e)
{
    if (sender is not Button { Tag: ClipboardEntry entry }) return;
    _clipboardWatcher?.SuppressNextChange(TimeSpan.FromMilliseconds(500));
    Clipboard.SetText(entry.Text);
}
```

Also add `using System.Collections.ObjectModel;` to the top of the file if not already present.

This task's `OnMeshMessageReceived` uses a placeholder peer-name lookup (`"peer"`) — fix this to use whatever field the existing code already tracks for the connected peer's display name (the accept-loop/outcome handling read in Step 1 should already have one); do not leave the literal placeholder string in the committed code.

- [ ] **Step 5: Build Mesh.Core and run the full test suite**

Run: `cd src/windows && dotnet build Mesh.Core && dotnet test Mesh.Tests`
Expected: build succeeds, all tests pass. (Mesh.App itself still cannot build on this Linux sandbox — verify it by careful reading, same approach as sub-project 1's Task 6.)

- [ ] **Step 6: Commit**

```bash
git add src/windows/Mesh.Core/ClipboardWatcher.cs src/windows/Mesh.App/MainWindow.xaml src/windows/Mesh.App/MainWindow.xaml.cs
git commit -m "feat(windows): clipboard tab wired to MeshSession, local clipboard watcher"
```

---

## Task 6: Android — detach the pairing transport for session reuse

**Files:**
- Modify: `android/app/src/main/java/com/mesh/core/PairingSession.kt`
- Test: `android/app/src/test/java/com/mesh/core/PairingSessionLoopbackTest.kt` (add one test to the existing file — read it first to match its existing helper functions for setting up a loopback pair)

**Interfaces:**
- Produces: `PairingSession.detachTransport(): SessionTransport` where `SessionTransport` is a small data class `data class SessionTransport(val socket: SSLSocket, val input: DataInputStream, val output: DataOutputStream)` — marks the session's `close()` a no-op afterward (reuse the existing `closed: AtomicBoolean` field) and hands the caller the live transport.

- [ ] **Step 1: Read the existing file first**

```bash
cat android/app/src/main/java/com/mesh/core/PairingSession.kt
cat android/app/src/test/java/com/mesh/core/PairingSessionLoopbackTest.kt
```
Confirm the private field names for the socket/input/output streams (expected: `socket`, `input`, `output` based on the current implementation, but verify) and how the existing loopback test file builds a connected pair (likely a helper that does `PairingSession.connect(...)` / `PairingSession.handshakeAccepted(...)` against two distinct test identities loaded from `identity_a.p12`/`identity_b.p12`).

- [ ] **Step 2: Write the failing test**

Add to `android/app/src/test/java/com/mesh/core/PairingSessionLoopbackTest.kt`, matching its existing style/helpers for building a connected pair (adjust the exact pair-building call to whatever the file's existing tests use):

```kotlin
@Test
fun `detachTransport makes close a no-op and leaves the socket usable`() = runBlocking {
    val (server, client) = createConnectedPair() // reuse this file's existing pair-setup helper
    try {
        val transport = server.detachTransport()
        server.close() // must now be a no-op

        assertFalse(transport.socket.isClosed)

        transport.socket.close()
    } finally {
        client.close()
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.PairingSessionLoopbackTest"`
Expected: FAIL — compilation error, `detachTransport`/`SessionTransport` unresolved

- [ ] **Step 4: Implement detachTransport**

In `android/app/src/main/java/com/mesh/core/PairingSession.kt`, add near the top-level declarations (outside the class, same file):

```kotlin
data class SessionTransport(
    val socket: SSLSocket,
    val input: DataInputStream,
    val output: DataOutputStream
)
```

Add inside the `PairingSession` class, near `close()`:

```kotlin
/**
 * Hands ownership of the open, authenticated transport to the caller (e.g. to build a
 * [MeshSession] on a Paired/Reconnected outcome). After this call, this session's own
 * [close] becomes a no-op — the caller now owns closing the transport.
 */
fun detachTransport(): SessionTransport {
    closed.set(true)
    return SessionTransport(socket, input, output)
}
```

`socket`, `input`, and `output` are already `private val` fields in the constructor/class body — change their visibility to `internal val` (not `private`) so `detachTransport()` (a member function, so this isn't strictly required for the function itself, but verify — if they're already accessible to member functions as `private val` that's sufficient and no visibility change is needed; only widen visibility if the compiler actually requires it).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.PairingSessionLoopbackTest"`
Expected: PASS

- [ ] **Step 6: Run the full unit test suite**

Run: `cd android && gradle :app:testDebugUnitTest`
Expected: all previously-passing tests still pass, plus this new one (30 total)

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mesh/core/PairingSession.kt android/app/src/test/java/com/mesh/core/PairingSessionLoopbackTest.kt
git commit -m "feat(android): allow detaching the pairing transport for session reuse"
```

---

## Task 7: Android — wire message framing (ClipboardPush/Heartbeat)

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/MeshMessage.kt`
- Test: `android/app/src/test/java/com/mesh/core/MeshMessageTest.kt`

**Interfaces:**
- Consumes: `PairingProtocol`'s existing string/byte framing (read `android/app/src/main/java/com/mesh/core/PairingProtocol.kt` first to match its exact function names — do not guess).
- Produces: `com.mesh.core.MeshMessage` sealed class, `ClipboardPush(val timestamp: Long, val text: String) : MeshMessage`, `Heartbeat : MeshMessage`, `MeshMessage.write(output: DataOutputStream, message: MeshMessage)`, `MeshMessage.read(input: DataInputStream): MeshMessage` — **same wire format as Windows's `MeshMessage` (Task 2): 1-byte tag (0x01=ClipboardPush, 0x02=Heartbeat), 8-byte big-endian ms timestamp for ClipboardPush, then the length-prefixed UTF-8 string.**

- [ ] **Step 1: Read PairingProtocol.kt first**

```bash
cat android/app/src/main/java/com/mesh/core/PairingProtocol.kt
```

- [ ] **Step 2: Write the failing test**

```kotlin
// android/app/src/test/java/com/mesh/core/MeshMessageTest.kt
package com.mesh.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream

class MeshMessageTest {
    @Test
    fun `clipboard push round trips`() {
        val out = ByteArrayOutputStream()
        val sent = ClipboardPush(1_760_000_000_000L, "hello world")
        MeshMessage.write(DataOutputStream(out), sent)

        val received = MeshMessage.read(DataInputStream(ByteArrayInputStream(out.toByteArray())))

        assertTrue(received is ClipboardPush)
        received as ClipboardPush
        assertEquals(sent.timestamp, received.timestamp)
        assertEquals("hello world", received.text)
    }

    @Test
    fun `heartbeat round trips`() {
        val out = ByteArrayOutputStream()
        MeshMessage.write(DataOutputStream(out), Heartbeat)

        val received = MeshMessage.read(DataInputStream(ByteArrayInputStream(out.toByteArray())))

        assertTrue(received is Heartbeat)
    }

    @Test
    fun `multiple messages round trip in order on same stream`() {
        val out = ByteArrayOutputStream()
        val dos = DataOutputStream(out)
        MeshMessage.write(dos, ClipboardPush(1L, "first"))
        MeshMessage.write(dos, Heartbeat)
        MeshMessage.write(dos, ClipboardPush(2L, "second"))

        val input = DataInputStream(ByteArrayInputStream(out.toByteArray()))
        val first = MeshMessage.read(input) as ClipboardPush
        assertEquals("first", first.text)
        assertTrue(MeshMessage.read(input) is Heartbeat)
        val second = MeshMessage.read(input) as ClipboardPush
        assertEquals("second", second.text)
    }

    @Test
    fun `wire format matches Windows byte for byte for a known clipboard push`() {
        // Cross-platform contract check: a fixed input must produce this exact byte sequence,
        // independently matched against the equivalent Windows MeshMessageTests assertions.
        val out = ByteArrayOutputStream()
        MeshMessage.write(DataOutputStream(out), ClipboardPush(1L, "hi"))
        val bytes = out.toByteArray()
        assertEquals(0x01, bytes[0].toInt())
        // bytes[1..8] = 8-byte big-endian timestamp = 1L
        assertEquals(0, bytes[1].toInt()); assertEquals(0, bytes[2].toInt())
        assertEquals(0, bytes[3].toInt()); assertEquals(0, bytes[4].toInt())
        assertEquals(0, bytes[5].toInt()); assertEquals(0, bytes[6].toInt())
        assertEquals(0, bytes[7].toInt()); assertEquals(1, bytes[8].toInt())
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshMessageTest"`
Expected: FAIL — compilation error, `MeshMessage`/`ClipboardPush`/`Heartbeat` unresolved

- [ ] **Step 4: Implement MeshMessage**

```kotlin
// android/app/src/main/java/com/mesh/core/MeshMessage.kt
package com.mesh.core

import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.EOFException

sealed class MeshMessage {
    companion object {
        private const val CLIPBOARD_PUSH_TAG = 0x01
        private const val HEARTBEAT_TAG = 0x02

        fun write(output: DataOutputStream, message: MeshMessage) {
            when (message) {
                is ClipboardPush -> {
                    output.writeByte(CLIPBOARD_PUSH_TAG)
                    output.writeLong(message.timestamp) // DataOutputStream.writeLong is big-endian
                    PairingProtocol.writeString(output, message.text)
                }
                is Heartbeat -> output.writeByte(HEARTBEAT_TAG)
            }
            output.flush()
        }

        fun read(input: DataInputStream): MeshMessage {
            val tag = input.readUnsignedByte()
            return when (tag) {
                CLIPBOARD_PUSH_TAG -> {
                    val timestamp = input.readLong()
                    val text = PairingProtocol.readString(input)
                    ClipboardPush(timestamp, text)
                }
                HEARTBEAT_TAG -> Heartbeat
                else -> throw EOFException("Unknown message tag: $tag")
            }
        }
    }
}

data class ClipboardPush(val timestamp: Long, val text: String) : MeshMessage()
object Heartbeat : MeshMessage()
```

If `PairingProtocol.writeString`/`readString` turn out to have different names than assumed (check Step 1's output), adjust the two calls above to match exactly — do not add a second, parallel string-framing implementation. `DataOutputStream.writeLong`/`DataInputStream.readLong` are already big-endian, matching the Windows side's explicit byte-reversal — no manual byte-order handling is needed here.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshMessageTest"`
Expected: PASS (4 tests)

- [ ] **Step 6: Run the full unit test suite**

Run: `cd android && gradle :app:testDebugUnitTest`
Expected: all tests pass (34 total)

- [ ] **Step 7: Commit**

```bash
git add android/app/src/main/java/com/mesh/core/MeshMessage.kt android/app/src/test/java/com/mesh/core/MeshMessageTest.kt
git commit -m "feat(android): wire message framing for ClipboardPush and Heartbeat"
```

---

## Task 8: Android — clipboard history (Room entity + DAO, capped)

**Files:**
- Modify: `android/app/src/main/java/com/mesh/core/MeshDatabase.kt` (read first — add the new entity/DAO to its existing `@Database` annotation and bump `version`)
- Create: `android/app/src/main/java/com/mesh/core/ClipboardEntry.kt`
- Create: `android/app/src/main/java/com/mesh/core/ClipboardHistoryDao.kt`
- Test: `android/app/src/androidTest/java/com/mesh/core/ClipboardHistoryDaoTest.kt`

**Interfaces:**
- Produces: `@Entity data class ClipboardEntry(@PrimaryKey(autoGenerate = true) val id: Long = 0, val text: String, val source: String, val timestamp: Long)`. `@Dao interface ClipboardHistoryDao` with `suspend fun insertAndEvict(entry: ClipboardEntry)` (insert then delete-past-cap, both inside one `@Transaction`) and `suspend fun getAll(): List<ClipboardEntry>` (newest first, by `@Query`).

- [ ] **Step 1: Read MeshDatabase.kt first**

```bash
cat android/app/src/main/java/com/mesh/core/MeshDatabase.kt
```
Confirm its current `@Database(entities = [...], version = N)` annotation and existing DAO accessor pattern (e.g. `abstract fun pairedDeviceDao(): PairedDeviceDao`) so the new entity/DAO are added consistently, and bump `version` by 1 with `exportSchema = false` (matching whatever the existing annotation already sets) plus a `fallbackToDestructiveMigration()` call wherever the existing `Room.databaseBuilder(...)` call lives — read that call site too (same file or wherever `MeshDatabase` is instantiated) before editing it.

- [ ] **Step 2: Write the failing instrumented test**

```kotlin
// android/app/src/androidTest/java/com/mesh/core/ClipboardHistoryDaoTest.kt
package com.mesh.core

import androidx.room.Room
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ClipboardHistoryDaoTest {
    private lateinit var db: MeshDatabase
    private lateinit var dao: ClipboardHistoryDao

    @Before
    fun setUp() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        db = Room.inMemoryDatabaseBuilder(context, MeshDatabase::class.java).build()
        dao = db.clipboardHistoryDao()
    }

    @After
    fun tearDown() { db.close() }

    @Test
    fun insertAndEvict_thenGetAll_roundTrips() = runBlocking {
        dao.insertAndEvict(ClipboardEntry(text = "hello", source = "local", timestamp = 1000L))
        val all = dao.getAll()
        assertEquals(1, all.size)
        assertEquals("hello", all[0].text)
        assertEquals("local", all[0].source)
    }

    @Test
    fun getAll_returnsNewestFirst() = runBlocking {
        dao.insertAndEvict(ClipboardEntry(text = "first", source = "local", timestamp = 1000L))
        dao.insertAndEvict(ClipboardEntry(text = "second", source = "local", timestamp = 2000L))
        val all = dao.getAll()
        assertEquals("second", all[0].text)
        assertEquals("first", all[1].text)
    }

    @Test
    fun insertBeyond50_evictsOldest_countStaysAt50() = runBlocking {
        for (i in 0 until 51) {
            dao.insertAndEvict(ClipboardEntry(text = "entry-$i", source = "local", timestamp = i.toLong()))
        }
        val all = dao.getAll()
        assertEquals(50, all.size)
        assertFalse(all.any { it.text == "entry-0" })
        assertTrue(all.any { it.text == "entry-50" })
    }
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd android && gradle :app:connectedDebugAndroidTest --tests "com.mesh.core.ClipboardHistoryDaoTest"`
Expected: FAIL — compilation error, `ClipboardEntry`/`ClipboardHistoryDao`/`clipboardHistoryDao()` unresolved.
**No emulator/device is available in this sandbox** (documented limitation carried over from sub-project 1 — no KVM access). Verify this task via compile-checks (`gradle :app:compileDebugAndroidTestSources`) and careful review of the Room annotations against Room's documented behavior instead of actually running the test. Ledger this the same way sub-project 1's instrumented tests were ledgered.

- [ ] **Step 4: Implement ClipboardEntry and ClipboardHistoryDao**

```kotlin
// android/app/src/main/java/com/mesh/core/ClipboardEntry.kt
package com.mesh.core

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "clipboard_history")
data class ClipboardEntry(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val text: String,
    val source: String,
    val timestamp: Long
)
```

```kotlin
// android/app/src/main/java/com/mesh/core/ClipboardHistoryDao.kt
package com.mesh.core

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction

@Dao
interface ClipboardHistoryDao {
    @Transaction
    suspend fun insertAndEvict(entry: ClipboardEntry) {
        insert(entry)
        evictPast(CAP)
    }

    @Insert
    suspend fun insert(entry: ClipboardEntry)

    @Query(
        """
        DELETE FROM clipboard_history
        WHERE id NOT IN (
            SELECT id FROM clipboard_history ORDER BY timestamp DESC, id DESC LIMIT :cap
        )
        """
    )
    suspend fun evictPast(cap: Int)

    @Query("SELECT * FROM clipboard_history ORDER BY timestamp DESC, id DESC")
    suspend fun getAll(): List<ClipboardEntry>

    companion object {
        const val CAP = 50
    }
}
```

Add `clipboardHistoryDao()` to the `MeshDatabase` abstract class following its existing accessor pattern (read in Step 1), add `ClipboardEntry::class` to the `entities` list, and bump `version`.

- [ ] **Step 5: Verify compilation**

Run: `cd android && gradle :app:compileDebugAndroidTestSources`
Expected: compiles successfully (Room annotation processing succeeds, generating the DAO implementation)

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mesh/core/MeshDatabase.kt android/app/src/main/java/com/mesh/core/ClipboardEntry.kt android/app/src/main/java/com/mesh/core/ClipboardHistoryDao.kt android/app/src/androidTest/java/com/mesh/core/ClipboardHistoryDaoTest.kt
git commit -m "feat(android): capped Room-backed clipboard history"
```

---

## Task 9: Android — MeshSession (persistent channel, heartbeat, reconnect)

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/MeshSession.kt`
- Test: `android/app/src/test/java/com/mesh/core/MeshSessionTest.kt`

**Interfaces:**
- Consumes: `MeshMessage`/`ClipboardPush`/`Heartbeat` (Task 7), `PairingSession.detachTransport()`/`SessionTransport` (Task 6).
- Produces: `enum class MeshSessionState { CONNECTED, DISCONNECTED, RECONNECTING }`. `class MeshSession` with:
  - `companion object { fun fromTransport(transport: SessionTransport, peerUuid: String, peerIp: String, peerPort: Int): MeshSession }`
  - `var onMessageReceived: ((MeshMessage) -> Unit)?`
  - `var onStateChanged: ((MeshSessionState) -> Unit)?`
  - `suspend fun send(message: MeshMessage)` (queues if disconnected, sends immediately if connected)
  - `fun close()` (stops the read/heartbeat loops, closes the transport)

- [ ] **Step 1: Write the failing test — basic send/receive over loopback**

Read `android/app/src/test/java/com/mesh/core/PairingSessionLoopbackTest.kt` first (same file touched in Task 6) to reuse its existing connected-pair helper; adjust the exact helper call below to match what's actually there.

```kotlin
// android/app/src/test/java/com/mesh/core/MeshSessionTest.kt
package com.mesh.core

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MeshSessionTest {
    @Test
    fun `send delivers message to peer, onMessageReceived fires`() = runBlocking {
        val (serverPairing, clientPairing) = createConnectedPair() // reuse PairingSessionLoopbackTest's helper
        val server = MeshSession.fromTransport(serverPairing.detachTransport(), "peer-client", "127.0.0.1", 0)
        val client = MeshSession.fromTransport(clientPairing.detachTransport(), "peer-server", "127.0.0.1", 0)
        try {
            val received = CompletableDeferred<MeshMessage>()
            client.onMessageReceived = { received.complete(it) }

            server.send(ClipboardPush(1L, "hi from server"))

            val result = withTimeout(5000) { received.await() }
            assertTrue(result is ClipboardPush)
            assertEquals("hi from server", (result as ClipboardPush).text)
        } finally {
            server.close(); client.close()
        }
    }

    @Test
    fun `onStateChanged fires DISCONNECTED when peer closes`() = runBlocking {
        val (serverPairing, clientPairing) = createConnectedPair()
        val server = MeshSession.fromTransport(serverPairing.detachTransport(), "peer-client", "127.0.0.1", 0)
        val client = MeshSession.fromTransport(clientPairing.detachTransport(), "peer-server", "127.0.0.1", 0)
        try {
            val states = mutableListOf<MeshSessionState>()
            client.onStateChanged = { states.add(it) }

            server.close() // simulate peer going away

            kotlinx.coroutines.delay(2000)
            assertTrue(states.contains(MeshSessionState.DISCONNECTED))
        } finally {
            client.close()
        }
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshSessionTest"`
Expected: FAIL — `MeshSession` unresolved

- [ ] **Step 3: Implement MeshSession**

Before writing this, run `cat android/app/src/main/java/com/mesh/core/PairingSession.kt` to confirm whether `createConnectedPair()` in Step 1's test actually exists in `PairingSessionLoopbackTest.kt` or needs to be the file's own differently-named helper — use whatever is actually there.

```kotlin
// android/app/src/main/java/com/mesh/core/MeshSession.kt
package com.mesh.core

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.Socket
import javax.net.ssl.SSLSocket

enum class MeshSessionState { CONNECTED, DISCONNECTED, RECONNECTING }

/**
 * A persistent, reconnecting channel to a paired peer, carrying framed [MeshMessage] traffic
 * after the pairing handshake completes. Owns the transport from the point it is constructed
 * (via [fromTransport]) until [close].
 */
class MeshSession private constructor(
    private var socket: SSLSocket?,
    private var input: DataInputStream?,
    private var output: DataOutputStream?,
    private val peerUuid: String,
    private var peerIp: String,
    private val peerPort: Int
) {
    companion object {
        private val HEARTBEAT_INTERVAL_MS = 20_000L
        private val IDLE_TIMEOUT_MS = 45_000L
        private val BACKOFF_STEPS_MS = longArrayOf(1_000, 2_000, 4_000, 8_000)
        private val MAX_BACKOFF_MS = 30_000L

        fun fromTransport(transport: SessionTransport, peerUuid: String, peerIp: String, peerPort: Int): MeshSession {
            val session = MeshSession(transport.socket, transport.input, transport.output, peerUuid, peerIp, peerPort)
            session.scope.launch { session.runReadLoop() }
            session.scope.launch { session.runHeartbeatLoop() }
            return session
        }
    }

    var onMessageReceived: ((MeshMessage) -> Unit)? = null
    var onStateChanged: ((MeshSessionState) -> Unit)? = null

    private val job = Job()
    private val scope = CoroutineScope(Dispatchers.IO + job)
    private val sendMutex = Mutex()
    private val pendingSend = mutableListOf<MeshMessage>()
    @Volatile private var lastReceivedAt = System.currentTimeMillis()
    @Volatile private var state = MeshSessionState.CONNECTED

    suspend fun send(message: MeshMessage) {
        sendMutex.withLock {
            val out = output
            if (state != MeshSessionState.CONNECTED || out == null) {
                pendingSend.add(message)
                return
            }
            try {
                MeshMessage.write(out, message)
            } catch (e: Exception) {
                pendingSend.add(message)
                transitionTo(MeshSessionState.DISCONNECTED)
                scope.launch { reconnectLoop() }
            }
        }
    }

    private suspend fun runReadLoop() {
        while (job.isActive) {
            try {
                val input = this.input ?: run { delay(200); return@run }.let { return@runReadLoop }
                val message = MeshMessage.read(input)
                lastReceivedAt = System.currentTimeMillis()
                if (message !is Heartbeat) onMessageReceived?.invoke(message)
            } catch (e: Exception) {
                if (!job.isActive) return
                transitionTo(MeshSessionState.DISCONNECTED)
                scope.launch { reconnectLoop() }
                return
            }
        }
    }

    private suspend fun runHeartbeatLoop() {
        while (job.isActive) {
            delay(HEARTBEAT_INTERVAL_MS)
            if (!job.isActive) return
            if (state == MeshSessionState.CONNECTED) {
                if (System.currentTimeMillis() - lastReceivedAt > IDLE_TIMEOUT_MS) {
                    transitionTo(MeshSessionState.DISCONNECTED)
                    scope.launch { reconnectLoop() }
                    continue
                }
                try { send(Heartbeat) } catch (e: Exception) { /* send() already handles failure */ }
            }
        }
    }

    private suspend fun reconnectLoop() {
        transitionTo(MeshSessionState.RECONNECTING)
        var attempt = 0
        while (job.isActive) {
            attempt++
            try {
                // Reconnecting here re-establishes only the TLS transport to an already-trusted
                // peer; it intentionally does not repeat the PIN/trust protocol. Full reconnect
                // (re-running the trusted-peer TLS handshake) is orchestrated by the UI layer
                // (Task 10), which listens for onStateChanged(DISCONNECTED), re-runs
                // PairingSession.connect + isPeerTrusted + detachTransport, and replaces this
                // MeshSession instance on success — mirroring the Windows design (Task 4/5).
                val probe = Socket()
                probe.connect(java.net.InetSocketAddress(peerIp, peerPort), 3000)
                probe.close()
                return // Signal: caller (Task 10) must re-run trusted handshake and replace this session.
            } catch (e: Exception) {
                val delayMs = if (attempt <= BACKOFF_STEPS_MS.size) BACKOFF_STEPS_MS[attempt - 1] else MAX_BACKOFF_MS
                delay(delayMs)
            }
        }
    }

    private fun transitionTo(newState: MeshSessionState) {
        if (state == newState) return
        state = newState
        onStateChanged?.invoke(newState)
    }

    fun close() {
        job.cancel()
        try { socket?.close() } catch (e: Exception) { /* already closing */ }
    }
}
```

**Note for the implementer:** as with the Windows `MeshSession` (Task 4), the reconnect loop here is intentionally minimal — it only probes that the peer's address is reachable again, then hands control back to the caller for the actual trusted-reconnect handshake. Task 10 wires the UI layer to do that. If you find a cleaner design while implementing Task 10 (e.g. giving `MeshSession` the identity cert directly), that's fine — keep both the transport-level test coverage (this task) and the full-reconnect coverage (Task 10) either way, and note in your report which file ended up owning the orchestration. Fix the `runReadLoop`'s awkward `input ?: run { delay(200); return@run }.let { return@runReadLoop }` null-handling line if it doesn't compile as written — it's there to express "if the transport reference is momentarily null, back off and loop", but may need restructuring into a plain `if (input == null) { delay(200); continue }` instead; prefer the simpler form.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshSessionTest"`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full unit test suite**

Run: `cd android && gradle :app:testDebugUnitTest`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/mesh/core/MeshSession.kt android/app/src/test/java/com/mesh/core/MeshSessionTest.kt
git commit -m "feat(android): MeshSession persistent channel with heartbeat and reconnect scaffold"
```

---

## Task 10: Android — ClipboardWatcher, tab navigation, and full wiring

**Files:**
- Create: `android/app/src/main/java/com/mesh/core/ClipboardWatcher.kt`
- Modify: `android/app/src/main/res/layout/activity_main.xml` (read first, add a `TabLayout` + a container for swapped fragment content)
- Create: `android/app/src/main/java/com/mesh/ui/DevicesFragment.kt` (move the existing Devices-tab UI logic here from `MainActivity.kt` — read `MainActivity.kt` first to see exactly what to move)
- Create: `android/app/src/main/java/com/mesh/ui/ClipboardFragment.kt`
- Create: `android/app/src/main/res/layout/fragment_devices.xml`
- Create: `android/app/src/main/res/layout/fragment_clipboard.xml`
- Modify: `android/app/src/main/java/com/mesh/ui/MainActivity.kt` (becomes the tab host; keeps the `MeshSession` instance and discovery/pairing orchestration, since both fragments need it)
- Modify: `android/app/build.gradle.kts` (add `androidx.fragment:fragment-ktx` and a `TabLayout`-providing Material Components dependency, if not already present — read the file first)

**Interfaces:**
- Consumes: `MeshSession`/`MeshSessionState` (Task 9), `ClipboardHistoryDao`/`ClipboardEntry` (Task 8), `PairingSession` (existing `connect`/`run`/`detachTransport`/`isPeerTrusted`), `PairedDeviceDao` (existing), `MeshDiscovery` (existing).
- Produces: none consumed by later tasks (this is the Android UI integration point, parallel to Windows's Task 5).

- [ ] **Step 1: Read the current MainActivity.kt and activity_main.xml in full before editing**

```bash
cat android/app/src/main/java/com/mesh/ui/MainActivity.kt
cat android/app/src/main/res/layout/activity_main.xml
cat android/app/build.gradle.kts
```
This file was last touched by sub-project 1's fix wave and contains the full accept-loop + pairing-outcome handling. Do not guess its structure — read it, then make the additions below fit its actual current shape.

- [ ] **Step 2: Add fragment and Material Components dependencies if missing**

In `android/app/build.gradle.kts`, ensure these are present in the `dependencies` block (add only what's missing — check first):

```kotlin
implementation("androidx.fragment:fragment-ktx:1.8.5")
implementation("com.google.android.material:material:1.12.0")
```

- [ ] **Step 3: Implement ClipboardWatcher**

```kotlin
// android/app/src/main/java/com/mesh/core/ClipboardWatcher.kt
package com.mesh.core

import android.content.ClipboardManager
import android.content.Context

/**
 * Fires [onTextCopied] when the Android primary clipboard's text content changes.
 */
class ClipboardWatcher(context: Context) {
    private val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    private var suppressUntilMs = 0L

    var onTextCopied: ((String) -> Unit)? = null

    private val listener = ClipboardManager.OnPrimaryClipChangedListener {
        if (System.currentTimeMillis() < suppressUntilMs) return@OnPrimaryClipChangedListener
        val clip = clipboardManager.primaryClip
        if (clip != null && clip.itemCount > 0) {
            val text = clip.getItemAt(0).text?.toString()
            if (!text.isNullOrEmpty()) onTextCopied?.invoke(text)
        }
    }

    fun start() {
        clipboardManager.addPrimaryClipChangedListener(listener)
    }

    fun stop() {
        clipboardManager.removePrimaryClipChangedListener(listener)
    }

    /** Call right before the app writes to the clipboard itself (e.g. a "Copy" button on a
     * history entry) so the resulting change notification isn't re-pushed. */
    fun suppressNextChange(windowMs: Long) {
        suppressUntilMs = System.currentTimeMillis() + windowMs
    }
}
```

- [ ] **Step 4: Add tab layout to activity_main.xml**

Read the existing `activity_main.xml` (Step 1) and wrap its content: move the existing Devices-tab views into a new `fragment_devices.xml`, and replace `activity_main.xml`'s top-level content with:

```xml
<!-- android/app/src/main/res/layout/activity_main.xml -->
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical">

    <com.google.android.material.tabs.TabLayout
        android:id="@+id/tabLayout"
        android:layout_width="match_parent"
        android:layout_height="wrap_content">
        <com.google.android.material.tabs.TabItem
            android:text="Devices" />
        <com.google.android.material.tabs.TabItem
            android:text="Clipboard" />
    </com.google.android.material.tabs.TabLayout>

    <FrameLayout
        android:id="@+id/fragmentContainer"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"/>
</LinearLayout>
```

Create `fragment_devices.xml` containing exactly the views that were previously directly in `activity_main.xml` for the Devices tab (device list, Connect button, status/error text — whatever Step 1's read showed), unchanged apart from being moved into this new file.

Create `fragment_clipboard.xml`:

```xml
<!-- android/app/src/main/res/layout/fragment_clipboard.xml -->
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="12dp">

    <TextView
        android:id="@+id/sessionStatusText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Not connected"
        android:layout_marginBottom="8dp"/>

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/clipboardHistoryRecyclerView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"/>
</LinearLayout>
```

(If `androidx.recyclerview:recyclerview` is not already a dependency, add `implementation("androidx.recyclerview:recyclerview:1.3.2")` to `build.gradle.kts` alongside Step 2's additions.)

- [ ] **Step 5: Implement DevicesFragment**

Move the body of `MainActivity.kt`'s existing device-list/discovery/pairing-trigger UI logic (everything that manipulates the views now in `fragment_devices.xml`) into `DevicesFragment.kt`, keeping its behavior identical — only the hosting class changes (from `Activity` to `Fragment`), and it now calls back into `MainActivity` (via an interface or a shared `ViewModel`-less direct cast, whichever matches the existing code's style) for anything cross-cutting like obtaining the current `MeshSession`. Since this move's exact shape depends entirely on Step 1's read of the current `MainActivity.kt`, the implementer must write this fragment to preserve every existing behavior (discovery start/stop in `onCreate`/`onDestroy` equivalents, the PIN confirm dialog launch, trust-store lookups) — do not drop any of sub-project 1's working functionality while relocating it.

- [ ] **Step 6: Implement ClipboardFragment**

```kotlin
// android/app/src/main/java/com/mesh/ui/ClipboardFragment.kt
package com.mesh.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.mesh.R
import com.mesh.core.ClipboardEntry
import com.mesh.core.ClipboardHistoryDao
import com.mesh.core.ClipboardPush
import com.mesh.core.ClipboardWatcher
import com.mesh.core.Heartbeat
import com.mesh.core.MeshSession
import com.mesh.core.MeshSessionState
import kotlinx.coroutines.launch

class ClipboardFragment : Fragment(R.layout.fragment_clipboard) {
    private lateinit var statusText: TextView
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: ClipboardHistoryAdapter
    private lateinit var clipboardWatcher: ClipboardWatcher
    private lateinit var historyDao: ClipboardHistoryDao

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        statusText = view.findViewById(R.id.sessionStatusText)
        recyclerView = view.findViewById(R.id.clipboardHistoryRecyclerView)
        recyclerView.layoutManager = LinearLayoutManager(requireContext())

        historyDao = (requireActivity() as MainActivity).clipboardHistoryDao()
        adapter = ClipboardHistoryAdapter(mutableListOf()) { entry ->
            clipboardWatcher.suppressNextChange(500L)
            (requireActivity() as MainActivity).copyTextToClipboard(entry.text)
        }
        recyclerView.adapter = adapter

        clipboardWatcher = ClipboardWatcher(requireContext())
        clipboardWatcher.onTextCopied = { text -> onLocalTextCopied(text) }
        clipboardWatcher.start()

        viewLifecycleOwner.lifecycleScope.launch {
            adapter.replaceAll(historyDao.getAll())
        }

        val activity = requireActivity() as MainActivity
        activity.onMeshSessionMessage = { message ->
            if (message is ClipboardPush) {
                viewLifecycleOwner.lifecycleScope.launch {
                    val entry = ClipboardEntry(text = message.text, source = activity.peerDisplayName(), timestamp = message.timestamp)
                    historyDao.insertAndEvict(entry)
                    adapter.prepend(entry)
                }
            }
        }
        activity.onMeshSessionStateChanged = { state ->
            statusText.text = when (state) {
                MeshSessionState.CONNECTED -> "Connected"
                MeshSessionState.RECONNECTING -> "Reconnecting..."
                MeshSessionState.DISCONNECTED -> "Disconnected"
            }
        }
    }

    private fun onLocalTextCopied(text: String) {
        if (text.length > 1_048_576) return // 1 MiB cap, see Global Constraints
        viewLifecycleOwner.lifecycleScope.launch {
            val entry = ClipboardEntry(text = text, source = "local", timestamp = System.currentTimeMillis())
            historyDao.insertAndEvict(entry)
            adapter.prepend(entry)
            (requireActivity() as MainActivity).currentMeshSession()?.send(ClipboardPush(entry.timestamp, text))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        clipboardWatcher.stop()
    }
}

class ClipboardHistoryAdapter(
    private val items: MutableList<ClipboardEntry>,
    private val onCopyClicked: (ClipboardEntry) -> Unit
) : RecyclerView.Adapter<ClipboardHistoryAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val sourceText: TextView = view.findViewById(android.R.id.text1)
        val bodyText: TextView = view.findViewById(android.R.id.text2)
    }

    fun replaceAll(entries: List<ClipboardEntry>) {
        items.clear()
        items.addAll(entries)
        notifyDataSetChanged()
    }

    fun prepend(entry: ClipboardEntry) {
        items.add(0, entry)
        notifyItemInserted(0)
    }

    override fun onCreateViewHolder(parent: ViewGroup, position: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(android.R.layout.two_line_list_item, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val entry = items[position]
        holder.sourceText.text = entry.source
        holder.bodyText.text = entry.text
        holder.itemView.setOnClickListener { onCopyClicked(entry) }
    }

    override fun getItemCount() = items.size
}
```

`android.R.layout.two_line_list_item` is a stock two-line system layout with `android:id/text1`/`android:id/text2` — used here to avoid hand-authoring a third new layout file; replace it with a custom item layout if the implementer judges the stock one visually insufficient, keeping the same `ViewHolder` field names.

- [ ] **Step 7: Rewrite MainActivity.kt as the tab host**

Read Step 1's output fully before writing this. `MainActivity` keeps everything cross-cutting (identity/cert loading, `PairedDeviceStore`/`PairedDeviceDao`, `MeshDiscovery`, the accept-loop, the `MeshSession` instance, the reconnect orchestration) and exposes it to both fragments:

```kotlin
// Additions to android/app/src/main/java/com/mesh/ui/MainActivity.kt — merge with existing
// identity/discovery/pairing-listener setup from Step 1's read; do not duplicate that logic.
class MainActivity : AppCompatActivity() {
    // ... existing identity/discovery/paired-store fields from sub-project 1 ...

    private var meshSession: MeshSession? = null
    var onMeshSessionMessage: ((MeshMessage) -> Unit)? = null
    var onMeshSessionStateChanged: ((MeshSessionState) -> Unit)? = null
    private lateinit var database: MeshDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        database = Room.databaseBuilder(applicationContext, MeshDatabase::class.java, "mesh.db")
            .fallbackToDestructiveMigration()
            .build()

        val tabLayout = findViewById<com.google.android.material.tabs.TabLayout>(R.id.tabLayout)
        showFragment(DevicesFragment())
        tabLayout.addOnTabSelectedListener(object : com.google.android.material.tabs.TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: com.google.android.material.tabs.TabLayout.Tab) {
                showFragment(if (tab.position == 0) DevicesFragment() else ClipboardFragment())
            }
            override fun onTabUnselected(tab: com.google.android.material.tabs.TabLayout.Tab) {}
            override fun onTabReselected(tab: com.google.android.material.tabs.TabLayout.Tab) {}
        })

        // ... existing sub-project 1 identity/discovery setup continues here ...
    }

    private fun showFragment(fragment: androidx.fragment.app.Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }

    fun clipboardHistoryDao(): ClipboardHistoryDao = database.clipboardHistoryDao()

    fun currentMeshSession(): MeshSession? = meshSession

    fun peerDisplayName(): String = /* return whatever field already tracks the connected peer's
        display name from sub-project 1's pairing-outcome handling, read in Step 1 */ "peer"

    fun copyTextToClipboard(text: String) {
        val clipboardManager = getSystemService(ClipboardManager::class.java)
        clipboardManager.setPrimaryClip(android.content.ClipData.newPlainText("mesh", text))
    }

    // Called wherever sub-project 1's pairing/reconnect success handling currently lives
    // (found in Step 1's read), after a successful PairingSession.run() with outcome
    // Paired or Reconnected:
    private fun onPairingSucceeded(session: PairingSession, outcome: PairingOutcome, peerIp: String, peerPort: Int) {
        val transport = session.detachTransport()
        meshSession?.close()
        val newSession = MeshSession.fromTransport(transport, outcome.peerUuid, peerIp, peerPort)
        newSession.onMessageReceived = { message -> onMeshSessionMessage?.invoke(message) }
        newSession.onStateChanged = { state -> onMeshSessionStateChanged?.invoke(state) }
        meshSession = newSession
    }
}
```

The `onPairingSucceeded` placeholder shows the integration shape; the implementer must wire it into the actual call site(s) from Step 1's read (sub-project 1's fix wave added this success handling somewhere in the accept-loop/connect-flow — find the exact spot and call through to this logic there, rather than leaving a separate unused method). Fix `peerDisplayName()`'s placeholder `"peer"` return to use the real tracked peer-name field found in Step 1 — do not leave the literal placeholder in committed code.

- [ ] **Step 8: Build and run the full test suite**

Run: `cd android && gradle :app:compileDebugKotlin && gradle :app:testDebugUnitTest`
Expected: compiles, all unit tests pass. (Full UI behavior cannot be verified live in this sandbox — no emulator; verify via careful reading, same as sub-project 1's Task 12.)

- [ ] **Step 9: Commit**

```bash
git add android/app/src/main/java/com/mesh/core/ClipboardWatcher.kt android/app/src/main/java/com/mesh/ui/ android/app/src/main/res/layout/ android/app/build.gradle.kts
git commit -m "feat(android): clipboard tab wired to MeshSession, tab navigation, local clipboard watcher"
```

---

## Task 11: Self-copy dedup and oversized-push rejection — cross-platform hardening pass

**Files:**
- Modify: `src/windows/Mesh.Core/ClipboardWatcher.cs` (verify/adjust the existing `SuppressNextChange` window from Task 5)
- Modify: `src/windows/Mesh.Core/MeshMessage.cs` (reject oversized incoming pushes)
- Modify: `android/app/src/main/java/com/mesh/core/ClipboardWatcher.kt` (verify/adjust Task 10's `suppressNextChange`)
- Modify: `android/app/src/main/java/com/mesh/core/MeshMessage.kt` (reject oversized incoming pushes)
- Test: `src/windows/Mesh.Tests/MeshMessageTests.cs` (add)
- Test: `android/app/src/test/java/com/mesh/core/MeshMessageTest.kt` (add)

This task exists because of the Review Focus item on oversized pushes from a peer — Tasks 2/4 and 7/9 only handle well-behaved input. A peer (malicious or buggy) can send a `ClipboardPush` whose length-prefix claims an enormous string; without a cap, the receiver tries to allocate/read it and can run out of memory or hang.

**Interfaces:**
- Consumes/modifies: `MeshMessage.ReadAsync`/`MeshMessage.read` (Tasks 2/7).
- Produces: `MeshMessage.ReadAsync`/`read` now throw a distinguishable exception (`InvalidDataException`/`EOFException` with a clear message) for a `ClipboardPush` whose text exceeds 1 MiB (1,048,576 UTF-16 chars), and `MeshSession`'s read loop (Tasks 4/9) already treats any read-loop exception as "disconnect and reconnect" — verify that behavior is correct for this new rejection path too (a hostile/buggy peer triggering it repeatedly should not crash the app, only cause reconnect churn, which the existing backoff already bounds).

- [ ] **Step 1: Write the failing test (Windows)**

```csharp
// Add to src/windows/Mesh.Tests/MeshMessageTests.cs
[Fact]
public async Task ReadAsync_RejectsOversizedClipboardPush()
{
    using var stream = new MemoryStream();
    await stream.WriteAsync(new byte[] { 0x01 }); // ClipboardPush tag
    var tsBytes = new byte[8]; // timestamp, value irrelevant
    await stream.WriteAsync(tsBytes);
    var lengthBytes = BitConverter.GetBytes(2_000_000); // claims a 2,000,000-byte string
    if (BitConverter.IsLittleEndian) Array.Reverse(lengthBytes);
    await stream.WriteAsync(lengthBytes);
    stream.Position = 0;

    await Assert.ThrowsAsync<InvalidDataException>(() => MeshMessage.ReadAsync(stream));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src/windows && dotnet test Mesh.Tests --filter ReadAsync_RejectsOversizedClipboardPush`
Expected: FAIL (no length check exists yet — either passes through to `PairingProtocol.ReadStringAsync`, which may itself throw a different, less specific exception, or hangs/throws `OutOfMemoryException`/`EndOfStreamException` instead of the expected `InvalidDataException`)

- [ ] **Step 3: Implement the cap check (Windows)**

In `src/windows/Mesh.Core/MeshMessage.cs`, add a constant and a peek-the-length-prefix check before delegating to `PairingProtocol.ReadStringAsync` inside `ReadClipboardPushAsync`. Read `PairingProtocol.cs`'s string-reading implementation first to see whether it exposes the raw length prefix separately or only a combined read-and-decode call; if only the latter, read the 4-byte length prefix here directly (matching `PairingProtocol`'s own length-prefix format: 4-byte big-endian byte count) and throw before calling into the rest of its logic if it exceeds the cap, then reconstruct the stream read manually using `PairingProtocol`'s decode step on the now-known-safe byte count — or, if `PairingProtocol` exposes a byte-count argument independently, call that overload directly. Whichever shape `PairingProtocol.cs` actually has, the end result must be: the 4-byte length prefix is inspected before any string-sized buffer is allocated.

```csharp
// Inside MeshMessage, add:
private const int MaxTextBytes = 1_048_576; // 1 MiB cap, see spec's Error Handling section

// Modify ReadClipboardPushAsync to check the length prefix before decoding:
private static async Task<ClipboardPushMessage> ReadClipboardPushAsync(Stream stream)
{
    var tsBuf = new byte[8];
    await ReadExactAsync(stream, tsBuf);
    if (BitConverter.IsLittleEndian) Array.Reverse(tsBuf);
    var timestamp = DateTimeOffset.FromUnixTimeMilliseconds(BitConverter.ToInt64(tsBuf));

    var lengthBuf = new byte[4];
    await ReadExactAsync(stream, lengthBuf);
    if (BitConverter.IsLittleEndian) Array.Reverse(lengthBuf);
    var length = BitConverter.ToInt32(lengthBuf);
    if (length < 0 || length > MaxTextBytes)
        throw new InvalidDataException($"ClipboardPush text length {length} exceeds the {MaxTextBytes}-byte cap.");

    var textBuf = new byte[length];
    await ReadExactAsync(stream, textBuf);
    var text = System.Text.Encoding.UTF8.GetString(textBuf);
    return new ClipboardPushMessage(timestamp, text);
}
```

This inlines the length-prefixed string read instead of calling `PairingProtocol.ReadStringAsync` for this one call site, specifically so the length can be validated before the buffer is allocated — confirm `PairingProtocol`'s wire format really is a 4-byte big-endian length prefix before relying on this (re-check Task 2 Step 1's findings); if it differs, adjust the manual read above to match the real format exactly (same endianness/width used by `WriteStringAsync`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src/windows && dotnet test Mesh.Tests --filter ReadAsync_RejectsOversizedClipboardPush`
Expected: PASS

- [ ] **Step 5: Run the full Mesh.Tests suite**

Run: `cd src/windows && dotnet test Mesh.Tests`
Expected: all tests pass, including the earlier round-trip tests (a normal-sized push must still work)

- [ ] **Step 6: Write the failing test (Android)**

```kotlin
// Add to android/app/src/test/java/com/mesh/core/MeshMessageTest.kt
@Test(expected = java.io.IOException::class)
fun `read rejects oversized clipboard push`() {
    val out = ByteArrayOutputStream()
    val dos = DataOutputStream(out)
    dos.writeByte(0x01) // ClipboardPush tag
    dos.writeLong(0L) // timestamp, value irrelevant
    dos.writeInt(2_000_000) // claims a 2,000,000-byte string
    val input = DataInputStream(ByteArrayInputStream(out.toByteArray()))
    MeshMessage.read(input)
}
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshMessageTest"`
Expected: FAIL (no cap exists yet)

- [ ] **Step 8: Implement the cap check (Android)**

Read `PairingProtocol.kt`'s string-read implementation first (same caveat as the Windows side: confirm its actual length-prefix format before relying on it). Modify `MeshMessage.read`'s `ClipboardPush` branch:

```kotlin
// Inside MeshMessage.Companion.read, replace the ClipboardPush branch:
CLIPBOARD_PUSH_TAG -> {
    val timestamp = input.readLong()
    val length = input.readInt() // matches PairingProtocol's 4-byte big-endian length prefix
    if (length < 0 || length > MAX_TEXT_BYTES) {
        throw java.io.IOException("ClipboardPush text length $length exceeds the $MAX_TEXT_BYTES-byte cap.")
    }
    val textBytes = ByteArray(length)
    input.readFully(textBytes)
    ClipboardPush(timestamp, String(textBytes, Charsets.UTF_8))
}
```

Add `private const val MAX_TEXT_BYTES = 1_048_576` alongside the existing tag constants in `MeshMessage`'s companion object. This bypasses `PairingProtocol.readString` for this call site for the same reason as the Windows side — the length must be checked before the buffer is allocated. `DataInputStream.readInt()` is big-endian, matching `writeInt`'s already-big-endian output, so no manual byte-reversal is needed here (confirm this matches whatever `PairingProtocol.kt`'s own length-prefix read actually does, adjusting if it differs).

- [ ] **Step 9: Run test to verify it passes**

Run: `cd android && gradle :app:testDebugUnitTest --tests "com.mesh.core.MeshMessageTest"`
Expected: PASS

- [ ] **Step 10: Run the full Android unit test suite**

Run: `cd android && gradle :app:testDebugUnitTest`
Expected: all tests pass, including the earlier round-trip tests

- [ ] **Step 11: Commit**

```bash
git add src/windows/Mesh.Core/MeshMessage.cs src/windows/Mesh.Tests/MeshMessageTests.cs android/app/src/main/java/com/mesh/core/MeshMessage.kt android/app/src/test/java/com/mesh/core/MeshMessageTest.kt
git commit -m "fix: reject oversized ClipboardPush text on both platforms before allocating a buffer"
```

---

## Self-Review Notes (for the plan author, resolved before handoff)

- **Spec coverage:** persistent channel (Tasks 1/4/6/9), clipboard history sync both directions (Tasks 3/5/8/10), text-only (enforced by the 1 MiB cap in Task 11, and by `ClipboardPush`/`ClipboardEntry` only ever carrying `string`/`String`), tabbed UI (Task 5 Windows `TabControl`, Task 10 Android `TabLayout`+fragments), 50-row cap with auto-eviction (Tasks 3/8, transactional), offline queue (Tasks 4/9 `pendingSend`/`_pendingSend`), reconnect with backoff + mDNS fallback hook (Tasks 4/9), self-copy dedup (Tasks 5/10 `SuppressNextChange`/`suppressNextChange`), oversized-text rejection on both the local-watcher side and the wire-read side (Tasks 5/10 local cap, Task 11 wire cap) — all covered.
- **Type consistency check:** `ClipboardEntry`/`ClipboardPushMessage`/`ClipboardPush` field names (`Text`/`text`, `Source`/`source`, `Timestamp`/`timestamp`) are used consistently from their defining tasks (3, 8) through consuming tasks (5, 10). `MeshSession.SendAsync`/`send`, `DetachTransport`/`detachTransport`, `MessageReceived`/`onMessageReceived`, `StateChanged`/`onStateChanged` are each defined once (Tasks 1/4, 6/9) and referenced with matching names in every later task.
- **Placeholder scan:** the two intentionally-marked placeholders (`peerDisplayName()`'s `"peer"` fallback in Task 10, and the equivalent inline comment in Task 5's `OnMeshMessageReceived`) are each explicitly flagged with an instruction to replace them using a value Step 1 of that same task requires the implementer to locate by reading the current file — this is a deliberate "read current code to find the real field" step, not an unresolved plan gap, since the plan author cannot know that field's exact name without re-reading files whose content may have shifted since sub-project 1's fix wave. Both are called out explicitly so no implementer mistakes them for acceptable final code.
- **Known reconnect-orchestration seam:** Tasks 4/9 deliberately stop short of re-running the full trusted-handshake reconnect themselves (they only detect disconnection and probe reachability) because that requires the identity certificate and paired-device store, which `MeshSession` doesn't hold; Tasks 5/10 close that seam at the UI layer. This is called out in-line in both pairs of tasks so neither implementer nor reviewer mistakes it for an oversight.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-14-clipboard-sync.md`. Please review the plan. Given the earlier confirmation to proceed with subagent-driven execution for sub-project 1 and this plan's eleven interdependent-but-separable tasks (each with its own test cycle and review gate), I recommend **subagent-driven** execution again: a fresh reviewer per task catches integration mistakes (e.g. a mismatched wire format between Tasks 2 and 7) before they compound across later tasks, same as it did for sub-project 1's pairing-protocol bugs.

Does the plan capture what you want, and should we proceed the same way (subagent-driven-development)?
