import os
import asyncio
import random
import json
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

import aiohttp
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import login_engine

from xC4 import *
from xP import JoinSq, OpenCh, MsqSq, ExitSq
from byte import Encrypt_ID, encrypt_api
from Pb2 import DEcwHisPErMsG_pb2, sQ_pb2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMOTES_PATH       = os.path.join(BASE_DIR, "emotes.json")
EMOTE_MENU_PATH   = os.path.join(BASE_DIR, "emote_menu.json")
SINGLE_EMOTE_PATH = os.path.join(BASE_DIR, "singele_emote.json")
SPAM_TARGETS_FILE = os.path.join(BASE_DIR, "spam_targets.json")
ACCES_PATH        = os.path.join(BASE_DIR, "acces.txt")

online_writer = None
whisper_writer = None
bot_uid = None
ToKen = None
region = None
admin_uid = "9230844760"

spm_tasks = {}
spm_stop_events = {}
bot_enabled = True
auto_accept_invites = False

EVO_IDS = [
    909000063, 909000075, 909040010, 909000081, 909039011,
    909045001, 909038012, 909042008, 909051003, 909035012,
    909000098, 909033002, 909037011, 909049010, 909041005,
    909038010, 909033001, 909035007, 909000090, 909000085,
    909000068
]

GENERAL_EMOTES_MAP = {}
EMOTE_MAP = {}
EMOTE_MENU = {}
SINGLE_EMOTES_MAP = {}

try:
    with open(EMOTES_PATH, "r", encoding="utf-8") as _f:
        _emote_list = json.load(_f)
    GENERAL_EMOTES_MAP = {str(item["Number"]): int(item["Id"]) for item in _emote_list}
    EMOTE_MAP = {int(item["Number"]): int(item["Id"]) for item in _emote_list}
except Exception:
    pass

try:
    with open(SINGLE_EMOTE_PATH, "r", encoding="utf-8") as _f:
        _single_list = json.load(_f)
    SINGLE_EMOTES_MAP = {str(item["Number"]): int(item["Id"]) for item in _single_list}
except Exception:
    pass

try:
    with open(EMOTE_MENU_PATH, "r", encoding="utf-8") as _f:
        EMOTE_MENU = json.load(_f)
except Exception:
    pass

NAME_EMOTES = {
    "ak": 909000063, "scar": 909000068, "mp40": 909000075,
    "m1014": 909000081, "xm8": 909000085, "famas": 909000090,
    "ump": 909000098, "m1887": 909035007, "woodpecker": 909042008,
    "groza": 909041005, "m4a1": 909033001, "thompson": 909038010,
    "g18": 909038012, "parafal": 909045001, "p90": 909049010,
    "m60": 909051003, "fist": 909037011, "ring": 909050009,
    "heart": 909038004, "love": 909000010, "dance": 909000027,
    "hello": 909000001, "hi": 909000001, "money": 909000129,
    "lol": 909000002, "sad": 909038005, "angry": 909000014,
    "chicken": 909000006, "dab": 909000005, "selfie": 909000040,
    "shower": 909051004, "flower": 909051002, "petals": 909051013,
}

def load_account():
    if not os.path.exists(ACCES_PATH):
        raise FileNotFoundError("acces.txt غير موجود")
    with open(ACCES_PATH, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    try:
        data = json.loads(raw)
        return str(data["uid"]), str(data["password"]), str(data.get("region", "ME"))
    except Exception:
        pass
    uid = pw = None
    reg = "ME"
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k in ("uid", "user", "username"):
                uid = v
            elif k in ("password", "pw", "pass"):
                pw = v
            elif k in ("region", "reg"):
                reg = v
    if not uid or not pw:
        raise ValueError("acces.txt غير صالح")
    return uid, pw, reg

def load_spam_targets():
    if os.path.exists(SPAM_TARGETS_FILE):
        with open(SPAM_TARGETS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_spam_targets():
    with open(SPAM_TARGETS_FILE, "w") as f:
        json.dump(list(spam_targets), f)

spam_targets = load_spam_targets()

def get_random_color():
    colors = [
        "[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]", "[FFFFFF]", "[FFA500]",
        "[A52A2A]", "[800080]", "[000000]", "[808080]", "[C0C0C0]", "[FFC0CB]", "[FFD700]", "[ADD8E6]",
        "[90EE90]", "[D2691E]", "[DC143C]", "[00CED1]", "[9400D3]", "[F08080]", "[20B2AA]", "[FF1493]",
        "[7CFC00]", "[B22222]", "[FF4500]", "[DAA520]", "[00BFFF]", "[00FF7F]", "[4682B4]", "[6495ED]",
        "[5F9EA0]", "[DDA0DD]", "[E6E6FA]", "[B0C4DE]", "[556B2F]", "[8FBC8F]", "[2E8B57]", "[3CB371]",
        "[6B8E23]", "[808000]", "[B8860B]", "[CD5C5C]", "[8B0000]", "[FF6347]", "[FF8C00]", "[BDB76B]"
    ]
    return random.choice(colors)

def get_random_avatar():
    return random.choice([902000003, 902000306])

def get_random_sticker():
    pack_id, start, end = random.choice([("1200000001", 1, 24), ("1200000004", 1, 15), ("1200000002", 1, 13)])
    return f"[1={pack_id}-{random.randint(start, end)}]"

def xMsGFixinG(n):
    return '|'.join(str(n)[i:i + 3] for i in range(0, len(str(n)), 3))

async def encrypt_packet(packet_hex, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(bytes.fromhex(packet_hex), AES.block_size)).hex()

def build_ob55_online_auth(account_uid, token, kts, key, iv):
    token_bytes = token.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc_token = cipher.encrypt(pad(token_bytes, 16))
    opcode = bytes.fromhex("830c")
    uid_bytes = int(account_uid).to_bytes(8, byteorder="big")
    kts_bytes = int(kts).to_bytes(4, byteorder="big")
    len_bytes = len(enc_token).to_bytes(8, byteorder="big")
    return opcode + uid_bytes + kts_bytes + len_bytes + enc_token, enc_token

def create_auth_token_chat(account_id, jwt_token, timestamp, key, iv):
    try:
        K = bytes.fromhex(key) if isinstance(key, str) else key
        V = bytes.fromhex(iv) if isinstance(iv, str) else iv
        ct = AES.new(K, AES.MODE_CBC, V).encrypt(pad(jwt_token.encode('utf-8'), AES.block_size))
        return (bytes.fromhex('6d19') + int(account_id).to_bytes(8, 'big') + int(timestamp).to_bytes(4, 'big') + len(ct).to_bytes(4, 'big') + ct).hex()
    except:
        return None

async def cHTypE(H):
    return 'Squid' if not H else 'CLan' if H == 1 else 'PrivaTe'

async def DecodeWhisperMessage(hex_packet):
    proto = DEcwHisPErMsG_pb2.DecodeWhisper()
    proto.ParseFromString(bytes.fromhex(hex_packet))
    return proto

async def get_colorful_message(message_text, message_number):
    color_palette = ["FF0000", "FFFF00", "0000FF", "FF00FF", "00FFFF", "FFA500", "FF1493", "00FF7F", "7B68EE", "FF66CC", "00CED1", "FF69B4"]
    return f"[C][B][{color_palette[(message_number - 1) % len(color_palette)]}]{message_text}"

async def NewClanChatPacket(message_text, key, iv, clan_id=3102281341):
    fields = {1: 16801068917, 2: 18, 4: 1, 5: {1: 16801068917, 2: clan_id, 3: 1, 4: 'SPY', 5: 1785944381, 7: 6, 9: {1: message_text, 4: 301, 8: 'SPY', 13: '', 14: {1: 16801068917}, 18: {1: 16801068917, 3: 1, 4: ''}}, 10: 'ar', 13: {2: 1, 3: 1}, 14: '', 16: int(time.time() * 1000)}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', key, iv)

async def SEndMsG(H, message, Uid, chat_id, key, iv):
    TypE = await cHTypE(H)
    if TypE == 'Squid':
        return await xSEndMsgsQ(message, chat_id, key, iv)
    elif TypE == 'CLan':
        return await NewClanChatPacket(message, key, iv, chat_id)
    elif TypE == 'PrivaTe':
        return await xSEndMsg(message, 2, Uid, Uid, key, iv)

async def SEndPacKeT(OnLinE, ChaT, TypE, PacKeT):
    if TypE == 'ChaT' and ChaT:
        whisper_writer.write(PacKeT)
        await whisper_writer.drain()
    elif TypE == 'OnLine':
        online_writer.write(PacKeT)
        await online_writer.drain()

async def safe_send_message(chat_type, message, uid, chat_id, key, iv, max_retries=3):
    for attempt in range(max_retries):
        try:
            packet = await SEndMsG(chat_type, message, uid, chat_id, key, iv)
            if packet:
                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', packet)
                return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False

async def JoinSq_original(code, K, V):
    skinz = {1: 4, 2: {4: "\u0001\u0007\t\n\u000b\u0012\u0019 '", 5: str(code), 6: 6, 8: 1,
        9: {1: "08FFF3BE903F27DF0203110111110000006B0003006800169194106F13CF106E4676251411010404dfe9e8b5ca3ca4f96a3119c00000004f03060301cacfa16d",
            2: 130, 3: "tY_S\u0013\b\u0001M\u0002\u0000T\u0000\u0005\u000e\b\t\u0002\u0000\u0003U\u0003\u0001V\u000fR\u000e\tRQ\u0002\u0004\u0005US\u0003XS\u0005\u0001\u0002\u0011\u0001\u0002JuTAEN\u001e\u0002\u001c\u0002\u001f\u0013\b\u0003M\u001cDbz_Q@}p_QOgsC\u001dYVI\u0004UAAj_ga\u0004\u0012\u0000K\u001d\u0007_t\u0019b\bCx\u0002UeGat\u001fTTCBLER`\u0006\u0001\r\f\u0012\u0006\u0005N^^\u0002acH~r\u0004_\u0003RO|\u000bcd_@~`Rnqrgh\n\u0015\nL\\Nh\u0000~G\u000et\u0000eb]VQ\u0006t^F[ZIGxCdZD\u000b\u0011\u0002OA~LP@\u000fcSDyATQApaT^{|wa]\\\u0001E\u000f\u0013\nJfxve}\u0004J\u0003c{YL\u0007^^yDYQf\bhe\u0005_wg\r\u0010\u0007\bEHpX@||\u0002Z\\uTGyA\u0001JP\u0005t~VkTE\u0000J\\\u000b\u0013\nMr\u0018zTzK}qE]vnvwROuheYvwduvQ\r\u001a\u0005M\u0006z\u001dfXfzvHFc~dXUz}O\u001aB\u0005t\u0002i\u001co_\u0004\u0012\u0003\u0007J\u0006b\u0003\u000eqlfvbEstgu~wB\u0001v@`yI\u0002ZPx\f\u0014\u0003NR\u0002yBZvuD_cd\u0004q]lH]\u0007bD}pCe\t\u0004t\n",
            4: "w^_R", 6: 11, 7: "\u0014\u0004aqrg\u0015\u0013", 8: "1.132.1", 9: 3, 10: 2,
            11: "\u0003bbSQ6wxegh9qAdV2KyoVleA17yPmYF+yTnOrl+JMknmppeUBe5ZsiHueP2mZZ4KOs6b2Ail1S9z3qIeU9hGFZ2M6PP39/zjIc/RFVPAkgDagySswMVmYaPhkzU5IqNPow2843fyQUz9xI10NdMhl1WiI4Y6wCXBotiUS9wSgujQ4j0fWXUyklCxBWo8r27hyoGSVrPdTPXFMnJJpPRRFFmWqc3fWvMg+BNfxSRJOZRSrkzG0nNvSIJ4uZB2pqAlHIPEYx7bI6zsgwUVDiLZJKTUTyuCGbOd1DegDUFfazFesTG1LJknT5WhgzCsrBIy+f2l+LeJe5DW7wEwNaHambM7ECXcJcLIhB9kJJsW0tFvXkk3HSdcQ8N1K6wjSKWhpkW0kV8Zrjj0jkhS/7AZ6T9GJRIA827YDtTorBvbx1UkXjYrqYI1nSa2GaMexGnqlurc5DE3v1R+mUBI9GqmjEPgTSYVBxyeCdQMHaMXGtspAhvkiO84ToU87sP45pylDEfFOVoc/rcmdzWeqlYPsv6txKRtIHcb0cO+MoVShoU8ZUVRDF3znbqzVrscPIfplBaa79lwvQqzRubLl9XY="},
        11: {1: "IDC4", 2: 281, 3: "ME"}, 13: "fr", 16: "7OR\u0019", 20: "\b\u0015", 27: "\bH\u0010\u0003"}}
    return await GeneRaTePk((await CrEaTe_ProTo(skinz)).hex(), '0515', K, V)

async def MahirAccepted(uid, code, K, V, region):
    fields = {1: 4, 2: {1: int(uid), 3: int(uid), 4: "rYUW\u0017\t\u0007NR\u000f\u0005\u0004\\W\u0002\u000fV\u0004TPQ\u0003\u000f\u0005\u0004]\u0005\u000b\u0000\u0002W\u0005\r\nVY\u0004\u0007\u0007\u0007\u0017\u0001\bNQ\fS\u0005\u000e\u0006\f\u0005\rT\u0002\r\u0000TS\u0007U\u0004X\u0006RY\u0005\u0003\u0003SW\u0000\u000eQ\u0000^\u0014\u0003\u0004JXS\u000f\u0000g{gqfePblEZJp{_xU\bmQW\f\u0007\u000f\u0015\u0007H\\U^CHXh@Ax`\u000f~\rPN~Nz\\\u001fr_ckPU\u000b\u0015\u0005\u0003Ekfp\u007fcY\u0001nWV\u0002\u0005azE~N\u0007HTg\u0007w}@\u0002{\t\u0013\u0001NeNP]DUf|]ugINs{\u0001\\rAgB_\u0004fA]\u0004\r\u001a\u0000HpOv\\\u0005|gS\u0019\\A\u007fWW\u0003\u007fTqFGi\u0004Qr\u0019dW\u0004\u0011\rD\u0002yeZ]A\u0016a\u0007Ungeg\u0007E\\P\u001b\u000b\u0004\u0005dd\ff\r\u000f\u0017\t\u000fNRyZd\u0012tZ\fe\u0007AGv\u007fw]{P\u001c\u007ff\u0005ZJK\u0004\u0005\u0014\u0001Jgq\u001frymsB\u0001\u000fd`\u001bj~[}\u0004SDZ|IxKB\u0000\n\u0011\u0002J^`tjYN\u0007WQdE[PQ\u0002_{VP`S\t\u007f\u001dP\n\u000f\u000f\u0015\u0004\u0004L{V\u0003@yP[rgJ{Hpk\u0001\u000bw\u0001Agt_\u0003HxPc\u000b\u0017\u0005E`y\ngWoy\u0006S{A\u001b``Y\u0002Xzw}dDWOKsg\t\u0013\u000eNf\u000e\\`\u0005AwJc\u0003BM\u0001^\u0000R\u0002Qoh]tbS~`G\r\u001a\u0004HibAQ\u000f^XNt~kDUWaeaNqcLQ]Py[G\u0004",
            8: 1, 9: {1: "08FBA33CFF105FDD02030A01111100000003000100020000B687046B0D6D2083467625141101030175a63c900e748c3f6a311e04000000ff00040202cacfa16d",
            2: 197, 3: "735154531406054a035305025a0e50560f5100040250020f5e0401520653000303505e0d520302501500064d705548424e1f051a001e12040a441d45677f5a56477574565e4f6274451d585849005a4f456d5b64670c1400496d017842740c670100040069536e72586c02016e657e566b524403081500044d0d515b637f757c19095c7c510b00417f565e5e066f5b584d6e02400a160e4d58496d0177400e750763605c575d0f7d5f475e5f4c407f4b60534b0b140549751e66407a4860726e44400e6103557e515c646f43577106077b60051b0f4b4e474e58457e4f615c01406000051e0361516e7b67614e040102540c1609004a0e40730f62517f446a135179507e706850547f7e7a67795553597c0a1206445b456640046265725c4d505d446d50737b7c42035970486370645e0b12034d506f5c7a1c554f574b0e765a0f0a7364505203477569456c6c420f0a1604014b647149136c186f795f5d78755e550e7842545e53747b08705f7f5d0a14004a08666b5a5b5f00045c7f5e584d72584262705f56055c61475564790515004b76514178587f52797a0f077a070953507d7f4d784f794f667b4256081b0e4a75627d4778417a06717574747c4c78557b4b7a0a697f0e714573600a",
            4: "{Y_R", 6: 13, 7: "1c6f017306741513", 8: "2.126.22", 9: 2, 10: 1,
            11: "036262535136784d584e38742b416456324b796f566c6537392f763672324d4773683377706379634f6b6b6f7447397934523930517432797246474c464c624c777a7747344d4d5257623146756d2b6556777a62597736743973492b787059612f55596e43465a59485235713348705830306c485a6f3632565145574e7145705866414c38734a754646575247386d376f5444566a4c484c576e714c52576f4e653236437a734c346a4144482b71694b55384d71476c5936546669544863716c487a345568463869396a365233366d49774b71746c36714f797568513854367945714b69742f45466d2b3636634b787649304f384d6c41385166454b6253467366477a2f30684e6a543873305369722f3962635a2f4679376c752f61632f366765704d415734566b442b36374f535756473665377a775a79312b797a42334b70632b7571782b577437414d39727761644439575765704570567849526d66654f5847627775787a68574b5664344c49586f415a364b387063647450627953575857455135706a542b653669365a2f6177444a3179356f774d5a534f64487262392b7877424a4d444f7848565a7a483372547a30314a316738517675466b656c3042433746473630683456427041494457487956684e794b4f5145507139467a4a6272686b316146306768766578512f6a2f484767426a5268675134645243372b477a5a687a2b77505967376454746f2b494d56363774642b54435653314234346b4148395a6d415872763758615941626477644e664f533170484875736b7336346f72463452534d3772656345417661484e61484854314c5545686e786a5a616d4d4f303d"},
            10: str(code), 11: {1: "IDC3", 2: 84, 3: "ME"}, 13: "en", 16: "374f5219",
            20: {1: 21}, 23: "a_1477547277882450725", 27: {1: 2, 2: 8}}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)

async def leave_channel_req(channel_id, channel_type, key, iv):
    fields = {1: 4, 2: {1: int(channel_id), 2: int(channel_type), 3: "en"}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '1215', key, iv)

async def SPamSqForSpm(Uid, K, V):
    same_value = random.choice([4096, 16384, 8192])
    fields = {1: 33, 2: {1: int(Uid), 2: "ME", 3: 1, 4: 1,
        5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]), 6: "iG:[C][B][FF0000] SPY",
        7: 330, 8: 1000, 10: "ME",
        11: bytes([49,97,99,52,98,56,48,101,99,102,48,52,55,56,97,52,52,50,48,51,98,102,56,102,97,99,54,49,50,48,102,53]),
        12: 1, 13: int(Uid),
        14: {1: 2203434355, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"},
        16: 1, 17: 1, 18: 312, 19: 46, 23: bytes([16, 1, 24, 1]),
        24: get_random_avatar(), 26: "", 28: "",
        31: {1: 1, 2: same_value}, 32: same_value,
        34: {1: int(Uid), 2: 8, 3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])}},
        10: "en", 13: {2: 1, 3: 1}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0515', K, V)

async def Room_Spam(Uid, Rm, Nm, K, V):
    fields = {1: 78, 2: {1: int(Rm), 2: "iG:[C][B][FF0000] SPY", 3: {2: 1, 3: 1},
        4: 330, 5: 6000, 6: 201, 10: get_random_avatar(), 11: int(Uid), 12: 1,
        15: {1: 1, 2: 32768}, 16: 32768,
        18: {1: 11481904755, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"},
        31: {1: 1, 2: 32768}, 32: 32768,
        34: {1: int(Uid), 2: 8, 3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])}}}
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), '0e15', K, V)

async def spm_loop(uid, key, iv, stop_event, interval=0.5):
    while not stop_event.is_set():
        try:
            if online_writer is not None:
                packet = await SPamSqForSpm(uid, key, iv)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', packet)
            else:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass

def get_help_message():
    c = get_random_color()
    return f"""[b][c]{c} بوت SPY

[b][c]{c}إنشاء فريق 5 لاعبين
[b][c][FFFFFF]/5

[b][c]{c}إنشاء فريق 3 لاعبين
[b][c][FFFFFF]/3

[b][c]{c}إنشاء فريق 6 لاعبين
[b][c][FFFFFF]/6

[b][c]{c}بدء السبام لمدة 30 دقيقة
[b][c][FFFFFF]/spm <uid>

[b][c]{c}إيقاف السبام
[b][c][FFFFFF]/stp <uid>

[b][c]{c}سبام الغرفة
[b][c][FFFFFF]/room <uid> <room_id>

[b][c]{c}إرسال رقصة إلى لاعبين داخل فريق
[b][c][FFFFFF]/em <team_code> <uid1> <uid2> ... <رقم الرقصة>

[b][c]{c}إرسال رقصة إيفو إلى لاعبين داخل فريق
[b][c][FFFFFF]/evo <team_code> <uid1> <uid2> ... <رقم الرقصة>

[b][c]{c}معلومات المطور
[b][c][FFFFFF]/admin"""

async def TcPOnLine(ip, port, key, iv, AutHToKen, reconnect_delay=0.5):
    global online_writer, auto_accept_invites
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            online_writer = writer
            token_bytes = bytes.fromhex(AutHToKen) if isinstance(AutHToKen, str) else AutHToKen
            writer.write(token_bytes)
            await writer.drain()
            while True:
                data = await reader.read(9999)
                if not data:
                    break
                hex_data = data.hex()
                if not hex_data.startswith("0500"):
                    continue
                try:
                    packet_json = json.loads(await DeCode_PackEt(hex_data[10:]))
                except Exception:
                    continue
                try:
                    if auto_accept_invites and ('5' in packet_json and 'data' in packet_json['5'] and '1' in packet_json['5']['data'] and '8' in packet_json['5']['data']):
                        owner = packet_json['5']['data']['1']['data']
                        code = packet_json['5']['data']['8']['data']
                        join_pkt = await MahirAccepted(owner, code, key, iv, region)
                        if join_pkt and online_writer:
                            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_pkt)
                except Exception:
                    pass
                try:
                    if auto_accept_invites:
                        uid_g = packet_json['5']['data']['1']['data']
                        chat_code = packet_json['5']['data']['17']['data']
                        if uid_g is not None:
                            INV_JOIN = await AutH_Chat(3, uid_g, chat_code, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', INV_JOIN)
                except Exception:
                    pass
                try:
                    if packet_json.get('4', {}).get('data') == 8:
                        f5 = packet_json.get('5', {}).get('data', {})
                        if f5.get('2', {}).get('data') == 5:
                            chat_code = f5.get('17', {}).get('data')
                            if chat_code is not None:
                                LeAvE = await leave_channel_req(chat_code, 3, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', LeAvE)
                except Exception:
                    pass
            writer.close()
            await writer.wait_closed()
            online_writer = None
        except Exception:
            online_writer = None
        await asyncio.sleep(reconnect_delay)

async def TcPChaT(ip, port, AutHToKen, key, iv, ready_event, region, reconnect_delay=0.5):
    global whisper_writer, online_writer, spm_tasks, spm_stop_events, bot_enabled
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            whisper_writer = writer
            bytes_payload = bytes.fromhex(AutHToKen) if isinstance(AutHToKen, str) else AutHToKen
            whisper_writer.write(bytes_payload)
            await whisper_writer.drain()
            ready_event.set()
            for tgt in spam_targets:
                if tgt not in spm_tasks or spm_tasks[tgt].done():
                    ev = asyncio.Event()
                    spm_stop_events[tgt] = ev
                    spm_tasks[tgt] = asyncio.create_task(spm_loop(tgt, key, iv, ev))
            while True:
                data = await reader.read(9999)
                if not data:
                    break
                if not data.hex().startswith("120000"):
                    continue
                try:
                    response = await DecodeWhisperMessage(data.hex()[10:])
                    uid = response.Data.uid
                    chat_id = response.Data.Chat_ID
                    XX = response.Data.chat_type
                    inPuTMsG = response.Data.msg.lower()
                except Exception:
                    continue
                command_text = inPuTMsG.strip()
                command = command_text.split()[0].split("@")[0].lower() if command_text else ""
                if not bot_enabled and command not in ("/on", "/admin", "/help", "help"):
                    continue
                if command in ("/help", "help") or command_text == "bot help":
                    try:
                        await safe_send_message(XX, get_help_message(), uid, chat_id, key, iv)
                    except Exception:
                        pass
                elif command in ("/admin", "admin"):
                    msg = f"""[b][c]{get_random_color()} بوت SPY

[b][c]{get_random_color()} الاسم: SPY
[b][c]{get_random_color()} بوت SPY ONLINE

[b][c]{get_random_color()} TELEGRAM: @SPY_FAKE"""
                    await safe_send_message(XX, msg, uid, chat_id, key, iv)
                elif inPuTMsG.strip() == '/on':
                    if str(uid) != admin_uid:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}فقط الأدمن يمكنه استخدام /on", uid, chat_id, key, iv)
                    else:
                        bot_enabled = True
                        await safe_send_message(XX, f"[B][C]{get_random_color()}البوت الآن قيد التشغيل", uid, chat_id, key, iv)
                elif inPuTMsG.strip() == '/off':
                    if str(uid) != admin_uid:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}فقط الأدمن يمكنه استخدام /off", uid, chat_id, key, iv)
                    else:
                        bot_enabled = False
                        await safe_send_message(XX, f"[B][C]{get_random_color()}البوت الآن متوقف", uid, chat_id, key, iv)
                elif inPuTMsG.startswith('/spm '):
                    parts = inPuTMsG.strip().split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        tgt = parts[1]
                        if tgt in spm_tasks:
                            if tgt in spm_stop_events:
                                spm_stop_events[tgt].set()
                            spm_tasks[tgt].cancel()
                        spam_targets.add(tgt)
                        save_spam_targets()
                        ev = asyncio.Event()
                        spm_stop_events[tgt] = ev
                        task = asyncio.create_task(spm_loop(tgt, key, iv, ev))
                        spm_tasks[tgt] = task
                        async def _auto_stop(t=tgt, e=ev):
                            try:
                                await asyncio.sleep(30 * 60)
                            except asyncio.CancelledError:
                                return
                            e.set()
                            if t in spm_tasks and not spm_tasks[t].done():
                                spm_tasks[t].cancel()
                            if t in spam_targets:
                                spam_targets.discard(t)
                                save_spam_targets()
                        asyncio.create_task(_auto_stop())
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم بدء السبام على {tgt} لمدة 30 دقيقة", uid, chat_id, key, iv)
                    else:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}الاستخدام: /spm <uid>", uid, chat_id, key, iv)
                elif inPuTMsG.startswith('/stp '):
                    parts = inPuTMsG.strip().split()
                    if len(parts) >= 2 and parts[1] in spm_tasks:
                        if parts[1] in spm_stop_events:
                            spm_stop_events[parts[1]].set()
                        spm_tasks[parts[1]].cancel()
                        del spm_tasks[parts[1]]
                        if parts[1] in spam_targets:
                            spam_targets.remove(parts[1])
                            save_spam_targets()
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إيقاف السبام", uid, chat_id, key, iv)
                    else:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}لا يوجد سبام نشط لهذا الـ UID", uid, chat_id, key, iv)
                elif inPuTMsG.startswith('/em '):
                    parts = inPuTMsG.strip().split()
                    try:
                        if len(parts) < 4:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}الاستخدام: /em <team_code> <uid1> <uid2> ... <رقم الرقصة>", uid, chat_id, key, iv)
                            continue
                        team_code = parts[1]
                        dance_num = parts[-1]
                        uids_l = [p for p in parts[2:-1] if p.isdigit()]
                        if not dance_num.isdigit() or dance_num not in SINGLE_EMOTES_MAP:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}رقم الرقصة '{dance_num}' غير موجود", uid, chat_id, key, iv)
                            continue
                        if not uids_l:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}لم يتم إدخال أي UID صالح", uid, chat_id, key, iv)
                            continue
                        join_pkt = await JoinSq_original(team_code, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_pkt)
                        await asyncio.sleep(1.5)
                        emote_id = SINGLE_EMOTES_MAP[dance_num]
                        sc = 0
                        for t in uids_l:
                            try:
                                H = await Emote_k(int(t), int(emote_id), key, iv, region)
                                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
                                sc += 1
                                await asyncio.sleep(0.15)
                            except Exception:
                                pass
                        await asyncio.sleep(0.5)
                        exit_pkt = await ExiT(uid, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', exit_pkt)
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إرسال الرقصة {dance_num} إلى {sc} اللاعب {team_code}", uid, chat_id, key, iv)
                    except Exception:
                        try:
                            exit_pkt = await ExiT(uid, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', exit_pkt)
                        except Exception:
                            pass
                elif inPuTMsG.startswith('/evo '):
                    parts = inPuTMsG.strip().split()
                    try:
                        if len(parts) < 4:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}الاستخدام: /evo <team_code> <uid1> <uid2> ... <رقم الرقصة>", uid, chat_id, key, iv)
                            continue
                        team_code = parts[1]
                        dance_num = parts[-1]
                        uids_l = [p for p in parts[2:-1] if p.isdigit()]
                        if not dance_num.isdigit() or int(dance_num) not in EMOTE_MAP:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}رقم الرقصة '{dance_num}' يجب أن يكون بين 1 و 21", uid, chat_id, key, iv)
                            continue
                        if not uids_l:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}لم يتم إدخال أي UID صالح", uid, chat_id, key, iv)
                            continue
                        join_pkt = await JoinSq_original(team_code, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_pkt)
                        await asyncio.sleep(1.5)
                        emote_id = EMOTE_MAP[int(dance_num)]
                        for t in uids_l:
                            try:
                                H = await Emote_k(int(t), int(emote_id), key, iv, region)
                                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', H)
                                await asyncio.sleep(0.15)
                            except Exception:
                                pass
                        await asyncio.sleep(0.5)
                        exit_pkt = await ExiT(uid, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', exit_pkt)
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إرسال رقصة إيفو {dance_num} إلى {len(uids_l)} اللاعب {team_code}", uid, chat_id, key, iv)
                    except Exception:
                        try:
                            exit_pkt = await ExiT(uid, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', exit_pkt)
                        except Exception:
                            pass
                elif inPuTMsG.startswith('/5') and not inPuTMsG.startswith('/50'):
                    try:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}جاري إنشاء فريق 5 لاعبين...", uid, chat_id, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await ExiT(uid, key, iv))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await OpEnSq(key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await cHSq(5, uid, key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await SEnd_InV(5, uid, key, iv, region))
                        await asyncio.sleep(3.5)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await ExiT(None, key, iv))
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إرسال دعوة فريق 5 لاعبين", uid, chat_id, key, iv)
                    except Exception:
                        pass
                elif inPuTMsG.startswith('/6'):
                    try:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}جاري إنشاء فريق 6 لاعبين...", uid, chat_id, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await ExiT(uid, key, iv))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await OpEnSq(key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await cHSq(6, uid, key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await SEnd_InV(6, uid, key, iv, region))
                        await asyncio.sleep(3.5)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await ExiT(None, key, iv))
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إرسال دعوة فريق 6 لاعبين", uid, chat_id, key, iv)
                    except Exception:
                        pass
                elif inPuTMsG.startswith('/3') and not inPuTMsG.startswith('/30'):
                    try:
                        await safe_send_message(XX, f"[B][C]{get_random_color()}جاري إنشاء فريق 3 لاعبين...", uid, chat_id, key, iv)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await OpEnSq(key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await cHSq(3, uid, key, iv, region))
                        await asyncio.sleep(0.3)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await SEnd_InV(3, uid, key, iv, region))
                        await asyncio.sleep(3.5)
                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', await ExiT(None, key, iv))
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إرسال دعوة فريق 3 لاعبين", uid, chat_id, key, iv)
                    except Exception:
                        pass
                elif inPuTMsG.strip().startswith('/room'):
                    parts = inPuTMsG.strip().split()
                    try:
                        if len(parts) < 3:
                            await safe_send_message(XX, f"[B][C]{get_random_color()}الاستخدام: /room <uid> <room_id>", uid, chat_id, key, iv)
                            continue
                        tgt = parts[1]
                        rid = parts[2]
                        if not tgt.isdigit() or not rid.isdigit():
                            await safe_send_message(XX, f"[B][C]{get_random_color()}قيمة غير صالحة، تأكد أن uid و room_id أرقام", uid, chat_id, key, iv)
                            continue
                        await safe_send_message(XX, f"[B][C]{get_random_color()}جاري بدء سبام الغرفة {rid} على UID {tgt} (1000 مرة)...", uid, chat_id, key, iv)
                        for i in range(1000):
                            spam_p = await Room_Spam(tgt, rid, "SPY", key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'OnLine', spam_p)
                            await asyncio.sleep(0.05)
                        await safe_send_message(XX, f"[B][C]{get_random_color()}تم إكمال سبام الغرفة", uid, chat_id, key, iv)
                    except Exception:
                        pass
                else:
                    pass
            writer.close()
            await writer.wait_closed()
            whisper_writer = None
        except Exception:
            whisper_writer = None
        await asyncio.sleep(reconnect_delay)

async def MaiiiinE():
    uid_val, pw_val, reg_val = load_account()
    result = await login_engine.do_login(uid_val, pw_val, reg_val)
    if not result:
        await asyncio.sleep(10)
        return
    global bot_uid, ToKen, region
    bot_uid = result["bot_uid"]
    ToKen = result["token"]
    region = result["region"]
    key = result["key"]
    iv = result["iv"]
    timestamp = result["timestamp"]
    online_ip = result["online_ip"]
    online_port = result["online_port"]
    chat_ip = result["chat_ip"]
    chat_port = result["chat_port"]
    acc_name = result["account_name"]
    print("✅ تم تشغيل البوت")
    print(f"اسم البوت: {acc_name}")
    print(f"السيرفر: {result['region']}")
    print(f"الايدي: {result['bot_uid']}")
    ChatAutH = create_auth_token_chat(int(result["bot_uid"]), result["token"], int(timestamp), key, iv)
    OnlineAutH, _ = build_ob55_online_auth(int(result["bot_uid"]), result["token"], int(timestamp), key, iv)
    ready_event = asyncio.Event()
    t1 = asyncio.create_task(TcPChaT(chat_ip, chat_port, ChatAutH, key, iv, ready_event, result["region"]))
    await ready_event.wait()
    await asyncio.sleep(1)
    t2 = asyncio.create_task(TcPOnLine(online_ip, online_port, key, iv, OnlineAutH))
    await asyncio.gather(t1, t2)

async def StarTinG():
    while True:
        try:
            await asyncio.wait_for(MaiiiinE(), timeout=7 * 60 * 60)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(StarTinG())
    except KeyboardInterrupt:
        pass