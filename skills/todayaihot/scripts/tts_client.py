"""火山引擎 seed-tts-2.0 双向流式 TTS（基于官方协议）
产出 PCM/WAV 音频，支持按句子合成，返回音频时长。
"""
import io, json, struct, sys, os, uuid, wave
import websocket
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import VOLC_API_KEY  # noqa: E402

ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
# API Key 从 common（环境变量/.env）加载，代码中不留明文
API_KEY = VOLC_API_KEY
RESOURCE_ID = "seed-tts-2.0"
VOICE = os.environ.get("VOLC_TTS_VOICE", "zh_female_sophie_uranus_bigtts")
SAMPLE_RATE = 24000
AUDIO_FORMAT = "pcm"

# ---- 枚举 ----
class MT:
    FullClientRequest = 0b1
    AudioOnlyClient = 0b10
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    Error = 0b1111

class EV:
    StartConnection = 1
    FinishConnection = 2
    ConnectionStarted = 50
    ConnectionFailed = 51
    ConnectionFinished = 52
    StartSession = 100
    CancelSession = 101
    FinishSession = 102
    SessionStarted = 150
    SessionCanceled = 151
    SessionFinished = 152
    SessionFailed = 153
    TaskRequest = 200
    TTSSentenceStart = 350
    TTSSentenceEnd = 351
    TTSResponse = 352


def build_frame(event, session_id="", payload=b"{}"):
    buf = io.BytesIO()
    buf.write(bytes([(1 << 4) | 1, (MT.FullClientRequest << 4) | 0b100, (1 << 4) | 0, 0]))
    buf.write(struct.pack(">i", event))
    if event not in (EV.StartConnection, EV.FinishConnection):
        sid = session_id.encode("utf-8")
        buf.write(struct.pack(">I", len(sid)))
        if sid:
            buf.write(sid)
    buf.write(struct.pack(">I", len(payload)))
    buf.write(payload)
    return buf.getvalue()


def parse_response(data):
    msg_type = data[1] >> 4
    flag = data[1] & 0x0F
    pos = 4
    event = struct.unpack(">i", data[pos:pos+4])[0] if flag & 0b100 else 0
    pos += 4
    session_id = ""
    if flag & 0b100 and event not in (EV.StartConnection, EV.FinishConnection,
                                      EV.ConnectionStarted, EV.ConnectionFailed, EV.ConnectionFinished):
        sid_len = struct.unpack(">I", data[pos:pos+4])[0]; pos += 4
        if sid_len:
            session_id = data[pos:pos+sid_len].decode("utf-8"); pos += sid_len
    payload = b""
    if pos + 4 <= len(data):
        plen = struct.unpack(">I", data[pos:pos+4])[0]; pos += 4
        if plen:
            payload = data[pos:pos+plen]
    return msg_type, event, session_id, payload


def headers():
    return {
        "X-Api-Key": API_KEY,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }


def synth_text(text: str, out_wav: str, verbose=False, speech_rate: int = 0, loudness_rate: int = 0,
               emotion: str = None, voice: str = None) -> float:
    """合成单段文本 -> wav，返回时长秒。"""
    ws = websocket.create_connection(ENDPOINT, header=headers(), timeout=60)
    try:
        ws.send(build_frame(EV.StartConnection, payload=b"{}"))
        while True:
            data = ws.recv()
            mt, ev, _, pl = parse_response(data)
            if mt == MT.FullServerResponse and ev == EV.ConnectionStarted:
                break
            if mt == MT.Error or (mt == MT.FullServerResponse and ev == EV.ConnectionFailed):
                raise RuntimeError(f"connect failed: {pl.decode('utf-8','ignore')}")

        base_req = {
            "speaker": voice or VOICE,
            "audio_params": {
                "format": AUDIO_FORMAT,
                "sample_rate": SAMPLE_RATE,
                "speech_rate": speech_rate,
                "loudness_rate": loudness_rate,
                **({"emotion": emotion} if emotion else {}),
            },
            "additions": json.dumps({"disable_markdown_filter": True}),
        }
        session_id = str(uuid.uuid4())
        session_req = {
            "user": {"uid": str(uuid.uuid4())},
            "namespace": "BidirectionalTTS",
            "event": EV.StartSession,
            "req_params": {**base_req},
        }
        ws.send(build_frame(EV.StartSession, session_id, json.dumps(session_req).encode()))
        while True:
            data = ws.recv()
            mt, ev, _, pl = parse_response(data)
            if mt == MT.FullServerResponse and ev == EV.SessionStarted:
                break
            if mt == MT.Error or (mt == MT.FullServerResponse and ev == EV.SessionFailed):
                raise RuntimeError(f"session failed: {pl.decode('utf-8','ignore')}")

        # 发送整段文本（可拆多个 TaskRequest，这里一次性发送）
        task_req = {
            "user": {"uid": str(uuid.uuid4())},
            "namespace": "BidirectionalTTS",
            "event": EV.TaskRequest,
            "req_params": {**base_req, "text": text},
        }
        ws.send(build_frame(EV.TaskRequest, session_id, json.dumps(task_req).encode()))
        ws.send(build_frame(EV.FinishSession, session_id, b"{}"))

        audio = bytearray()
        while True:
            data = ws.recv()
            mt, ev, _, pl = parse_response(data)
            if mt == MT.AudioOnlyServer:
                audio.extend(pl)
            elif mt == MT.FullServerResponse:
                if ev == EV.SessionFinished:
                    break
                if ev == EV.SessionFailed:
                    raise RuntimeError(f"session failed: {pl.decode('utf-8','ignore')}")
            elif mt == MT.Error:
                raise RuntimeError(f"err: {pl.decode('utf-8','ignore')}")
        try:
            ws.send(build_frame(EV.FinishConnection, payload=b"{}"))
            ws.recv()
        except Exception:
            pass
    finally:
        try:
            ws.close()
        except Exception:
            pass

    if not audio:
        raise RuntimeError("empty audio")
    pcm = bytes(audio)
    dur = len(pcm) / 2 / SAMPLE_RATE
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(pcm)
    if verbose:
        print(f"OK {out_wav} {len(pcm)}B {dur:.2f}s")
    return dur


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "GLM-5.3 正式发布，这是面向真实项目的一次实测。"
    out = sys.argv[2] if len(sys.argv) > 2 else "test2.wav"
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    try:
        d = synth_text(text, out, verbose=True)
        print(f"RESULT duration={d:.3f}s")
    except Exception as e:
        print("FAIL:", e)
        sys.exit(1)
