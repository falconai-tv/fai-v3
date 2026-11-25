from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Channel:
    name: str
    url: str
    category: str = "general"
    language: str = "multi"
    country: str = "global"
    tags: Optional[List[str]] = None
    is_live: bool = True


CHANNELS = [
    # ── ALBANIAN / KOSOVO ──────────────────────────────────────────────────────
    Channel("Kohavision", "https://gjirafa-video-live.gjirafa.net/gjvideo-livestream/lj9-pxm-o53-rp0/tracks-v4a1/mono.m3u8",
            "news", "sq", "kosovo", ["news", "albanian", "kosovo", "entertainment", "culture", "balkans", "live"]),
    Channel("RTK 3", "https://gjirafa-video-live.gjirafa.net/gjvideo-livestream/rtk3/index.m3u8",
            "news", "sq", "kosovo", ["news", "documentary", "culture", "education", "albanian", "kosovo", "balkans", "live"]),
    Channel("RTV21", "https://gjirafa-video-live.gjirafa.net/gjvideo-live/2cz-npl-jfn-9he/tracks-v2a1/mono.m3u8",
            "entertainment", "sq", "kosovo", ["news", "entertainment", "drama", "talk show", "albanian", "kosovo", "balkans", "live"]),
    Channel("T7", "https://gjirafa-video-live.gjirafa.net/gjvideo-livestream-specific/1z8-byc-4ee-lc9/index.m3u8",
            "news", "sq", "kosovo", ["news", "politics", "entertainment", "reality tv", "albanian", "kosovo", "balkans", "live"]),
    Channel("TV Arbëria 1", "https://yayin30.haber100.com/live/rtvarberia/playlist.m3u8",
            "entertainment", "sq", "kosovo", ["news", "entertainment", "culture", "albanian", "kosovo", "balkans", "live"]),
    Channel("TV Arbëria 3 Fëmijë", "https://ssh101.bozztv.com/ssh101/rtvarberia3/playlist.m3u8",
            "kids", "sq", "kosovo", ["kids", "children", "cartoons", "education", "albanian", "live"]),
    Channel("TV Arbëria 4 Muzikë", "https://ssh101.bozztv.com/ssh101/rtvarberia4/playlist.m3u8",
            "music", "sq", "kosovo", ["music", "music videos", "pop", "folk music", "albanian", "live"]),
    Channel("TV Arbëria Retro Hits", "https://ssh101.bozztv.com/ssh101/rtvarberiaretro/playlist.m3u8",
            "music", "sq", "kosovo", ["music", "retro", "classic", "oldies", "albanian", "live"]),
    Channel("TV Arta", "https://gjirafa-video-live.gjirafa.net/gjvideo-live/mps-vgx-u9p-qv1/index.m3u8",
            "news", "sq", "kosovo", ["news", "politics", "breaking news", "albanian", "kosovo", "balkans", "live"]),
    Channel("TV Dielli", "http://stream.tvdielli.com:8081/dielli/index.m3u8",
            "entertainment", "sq", "kosovo", ["local news", "entertainment", "culture", "music", "albanian", "balkans", "live"]),
    Channel("TV Opoja", "http://ip.opoja.tv:1935/tvopoja/tvopoja/playlist.m3u8",
            "entertainment", "sq", "kosovo", ["local news", "regional", "culture", "albanian", "balkans", "live"]),
    Channel("TV Syri", "https://gjirafa-video-live.gjirafa.net/gjvideo-live/xej-xnb-ba0-kup/index.m3u8",
            "news", "sq", "kosovo", ["news", "politics", "talk show", "albanian", "kosovo", "albania", "balkans", "live"]),
    Channel("Drita TV", "https://dritatv.protokolldns.xyz/dritaweb5587989/index.m3u8",
            "entertainment", "sq", "kosovo", ["albanian", "kosovo", "entertainment", "music", "culture", "balkans", "live"]),
    Channel("RTV Pendimi", "https://www.rtvpendimi.com:19360/tvpendimi/tvpendimi.m3u8",
            "religious", "sq", "kosovo", ["islamic", "religious", "albanian", "kosovo", "balkans", "live"]),
    Channel("RTV Islam", "https://protokolldns.xyz/rtvislamweb554/index.m3u8",
            "religious", "sq", "kosovo", ["islamic", "religious", "albanian", "kosovo", "balkans", "live"]),
    Channel("Alsat TV", "https://vipottbpkstream.vip.hr/Content/onevip-hls/Live/Channel(Alsat_M)/index.m3u8",
            "news", "sq", "north-macedonia", ["news", "politics", "albanian", "macedonia", "balkans", "live"]),
    Channel("Euronews Albania", "https://gjirafa-video-live.gjirafa.net/gjvideo-live/2dw-zuf-1c9-pxu/index.m3u8",
            "news", "sq", "albania", ["news", "world news", "albanian", "albania", "balkans", "live"]),
    Channel("News 24 Albania", "http://tv.balkanweb.com:8081/news24/livestream/playlist.m3u8",
            "news", "sq", "albania", ["news", "politics", "talk show", "albanian", "albania", "balkans", "live"]),
    Channel("Ora News", "https://live1.mediadesk.al/oranews.m3u8",
            "news", "sq", "albania", ["news", "politics", "entertainment", "albanian", "albania", "balkans", "live"]),
    Channel("Report TV", "https://deb10stream.duckdns.org/hls/stream.m3u8",
            "news", "sq", "albania", ["news", "politics", "investigation", "albanian", "albania", "balkans", "live"]),
    Channel("RTSH 1", "http://178.33.11.6:8696/live/rtsh1ott/playlist.m3u8",
            "entertainment", "sq", "albania", ["news", "entertainment", "culture", "drama", "albanian", "albania", "balkans", "live"]),
    Channel("RTSH 2", "http://178.33.11.6:8696/live/rtsh2/playlist.m3u8",
            "entertainment", "sq", "albania", ["culture", "education", "documentary", "sports", "albanian", "albania", "balkans", "live"]),
    Channel("RTSH 24", "http://178.33.11.6:8696/live/rtsh24/playlist.m3u8",
            "news", "sq", "albania", ["news", "breaking news", "politics", "albanian", "albania", "balkans", "live"]),
    Channel("RTSH Shqip", "http://178.33.11.6:8696/live/rtshshqip/playlist.m3u8",
            "entertainment", "sq", "albania", ["culture", "history", "archives", "classic", "albanian", "albania", "balkans", "live"]),
    Channel("RTSH Sport", "http://178.33.11.6:8696/live/rtshsport/playlist.m3u8",
            "sports", "sq", "albania", ["sports", "football", "live sports", "albanian", "albania", "balkans", "live"]),
    Channel("Syri", "https://stream.syritv.al/live/syritv/playlist.m3u8",
            "news", "sq", "albania", ["news", "politics", "talk show", "albanian", "albania", "balkans", "live"]),
    Channel("Vizion Plus", "https://tringliveviz.akamaized.net/delta/105/out/u/qwaszxerdfcvrtryuy.m3u8",
            "entertainment", "sq", "albania", ["entertainment", "news", "drama", "series", "movies", "albanian", "albania", "balkans", "live"]),
    Channel("CNA", "https://live1.mediadesk.al/cnatvlive.m3u8",
            "news", "sq", "albania", ["news", "politics", "commentary", "albanian", "albania", "balkans", "live"]),
    Channel("AlbKanale Music TV", "https://albportal.net/albkanalemusic.m3u8",
            "music", "sq", "albania", ["music", "music videos", "pop", "folk music", "albanian", "balkans", "live"]),
    Channel("Bang Bang", "https://digitalb-live.morescreens.com/DAL_1_004/playlist.m3u8?application_id=backoffice1&application_installation_id=1&authority_instance_id=spectar-prd-digitalb&detected_delivery_method=hls&id=DAL_1_004&playlist_template=nginx&profile_id=1&ps=6ca6054c4d6f9fafd6e3202ad620d4cc30ee45fdbbf1526cab3fdcac143b283d2f7251b3babf442b3a4fb90820abcc0cfaab2bff9a76799adc92b09fa0151f25&subscriber_id=1&token=142cda7d50870275a9ca7988ff001b32ab30709b&uuid=backoffice1&vh=7edb2a069c1d9e1872251cc87e99c568dfd18769f97905bd1dcaf519b259c970f880a1c43b6a7392ac496426adb0e55a2f6dbb06981536af9c1c987416282783&video_id=16377",
            "kids", "sq", "albania", ["kids", "children", "cartoons", "animation", "albanian", "albania", "live"]),
    Channel("Cufo", "https://digitalb-live.morescreens.com/DAL_1_005/playlist.m3u8?application_id=backoffice1&application_installation_id=1&authority_instance_id=spectar-prd-digitalb&detected_delivery_method=hls&id=DAL_1_005&playlist_template=nginx&profile_id=1&ps=94d0066599d8f74d1c090e93ac4617b6491d3629d2e2d770870fcef1f7effa25b204aa53b3821da5e9e65bee8e94331bcae2cb344d0739ca3a938b4ef2051cc8&subscriber_id=1&token=142cda7d50870275a9ca7988ff001b32ab30709b&uuid=backoffice1&vh=7ab82e63aae8510c6b37ea16da502e54e441a5a1a88bce0c8ed63da99bce948d86253d64ae00424dda8b9c8b6e2cd0f6cd79d8b0a56e10759210cdf4f6761d11&video_id=12498",
            "kids", "sq", "albania", ["kids", "children", "cartoons", "animation", "albanian", "albania", "live"]),

    # ── INTERNATIONAL NEWS ─────────────────────────────────────────────────────
    Channel("DW News", "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/master.m3u8",
            "news", "en", "germany", ["news", "world", "international", "politics", "europe", "germany", "dw", "deutsche welle", "live"]),
    Channel("DW English", "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/master.m3u8",
            "news", "en", "germany", ["news", "world", "international", "germany", "dw", "live"]),
    Channel("DW Arabic", "https://dwamdstream103.akamaized.net/hls/live/2015526/dwstream103/master.m3u8",
            "news", "ar", "germany", ["news", "arabic", "dw", "middle east", "live"]),
    Channel("TRT World", "https://tv-trtworld.medya.trt.com.tr/master.m3u8",
            "news", "en", "turkey", ["news", "world", "turkey", "trt", "international", "live"]),
    Channel("Africa News", "https://euronews-africanews-1-us.samsung.wurl.com/manifest/playlist.m3u8",
            "news", "en", "france", ["news", "africa", "africanews", "international", "live"]),
    Channel("Africanews English", "https://d35j45z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/africanews/africanews-en.m3u8",
            "news", "en", "global", ["news", "africa", "world", "english", "live"]),
    Channel("BBC News", "https://viamotionhsi.netplus.ch/live/eds/bbcworld/browser-HLS8/bbcworld.m3u8",
            "news", "en", "uk", ["news", "world news", "bbc", "politics", "uk", "british", "international", "live"]),
    Channel("France 24 French", "https://live.france24.com/hls/live/2037179/F24_FR_HI_HLS/master_5000.m3u8",
            "news", "fr", "france", ["news", "france", "french", "world", "politics", "live"]),
    Channel("BFM TV", "https://viamotionhsi.netplus.ch/live/eds/bfmtv/browser-HLS8/bfmtv.m3u8",
            "news", "fr", "france", ["news", "france", "french", "breaking news", "politics", "live"]),
    Channel("CNews HD", "https://viamotionhsi.netplus.ch/live/eds/itele/browser-HLS8/itele.m3u8",
            "news", "fr", "france", ["news", "france", "french", "politics", "commentary", "live"]),
    Channel("ABC News Live", "https://content.uplynk.com/channel/3324f2467c414329b3b0cc5cd987b6be.m3u8",
            "news", "en", "usa", ["news", "usa", "abc", "breaking news", "american", "live"]),
    Channel("Bloomberg TV US", "https://bloomberg.com/media-manifest/streams/us.m3u8",
            "news", "en", "usa", ["news", "finance", "business", "economy", "stocks", "markets", "financial", "bursa", "bloomberg", "usa", "live"]),
    Channel("CBS Sports Golazo", "https://dai.google.com/linear/hls/event/GxrCGmwST0ixsrc_QgB6qw/master.m3u8",
            "sports", "en", "usa", ["sports", "soccer", "football", "cbs", "live"]),
    Channel("Cheddar News", "https://cheddar-us.samsung.wurl.tv/playlist.m3u8",
            "news", "en", "usa", ["news", "business", "technology", "finance", "markets", "usa", "live"]),
    Channel("Court TV", "https://content.uplynk.com/channel/6c0bd0f94b1d4526a98676e9699a10ef.m3u8",
            "news", "en", "usa", ["news", "legal", "crime", "trials", "usa", "live"]),
    Channel("Fox Weather", "https://247wlive.foxweather.com/stream/index.m3u8",
            "news", "en", "usa", ["weather", "forecast", "fox", "usa", "live"]),
    Channel("Fox News Radio", "https://radiovid.foxnews.com/hls/live/661547/RADIOVID/index.m3u8",
            "news", "en", "usa", ["news", "politics", "fox", "radio", "usa", "live"]),
    Channel("LiveNOW from FOX", "https://fox-foxnewsnow-vizio.amagi.tv/playlist.m3u8",
            "news", "en", "usa", ["news", "breaking news", "fox", "usa", "live"]),
    Channel("NBC Los Angeles", "https://nbculocallive.akamaized.net/hls/live/2037084/losangeles/stream1/master.m3u8",
            "news", "en", "usa", ["news", "local", "nbc", "los angeles", "california", "usa", "live"]),
    Channel("FOX 11 Los Angeles", "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg00488-foxdigital-fox11losangeleskttv-vizious/playlist.m3u8",
            "news", "en", "usa", ["news", "local", "fox", "los angeles", "california", "usa", "live"]),
    Channel("Newsmax TV", "https://nmx1ota.akamaized.net/hls/live/2107010/Live_1/index.m3u8",
            "news", "en", "usa", ["news", "politics", "newsmax", "conservative", "usa", "live"]),
    Channel("NTD TV English", "https://amg17596-amg17596c1-ntdtv-worldwide-3276.playouts.now.amagi.tv/playlist/amg17596-newtangdynastytelevision-ntdtv-ntdtvworldwide/playlist.m3u8",
            "news", "en", "global", ["news", "world", "ntd", "china", "live"]),
    Channel("UN Web TV", "https://cdnapi.kaltura.com/p/2503451/sp/250345100/playManifest/entryId/1_gb6tjmle/protocol/https/format/applehttp/a.m3u8",
            "news", "en", "global", ["news", "united nations", "international", "politics", "live"]),
    Channel("VOA TV Africa", "https://voa-ingest.akamaized.net/hls/live/2033874/tvmc06/playlist.m3u8",
            "news", "en", "usa", ["news", "africa", "voa", "voice of america", "live"]),

    # ── ENTERTAINMENT / GENERAL ────────────────────────────────────────────────
    Channel("NASA TV", "https://ntvpublic-v2.akamaized.net/hls/live/2028660/NTV-Public-V2/master.m3u8",
            "education", "en", "usa", ["space", "science", "nasa", "education", "documentary", "live"]),
    Channel("Red Bull TV", "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
            "sports", "en", "global", ["sports", "extreme sports", "red bull", "adventure", "racing", "live"]),
    Channel("History Hit", "https://amg00426-lds-amg00426c2-samsung-ph-4623.playouts.now.amagi.tv/playlist.m3u8",
            "education", "en", "global", ["history", "documentary", "education", "military", "live"]),
    Channel("WildEarth", "https://cdn-ue1-prod.tsv2.amagi.tv/linear/amg01290-wildearth-oando/playlist.m3u8",
            "education", "en", "global", ["nature", "wildlife", "animals", "safari", "documentary", "live"]),
    Channel("Animal Kingdom", "https://cdn6.goprimetime.info/feed/202306140918/LC18/index.m3u8",
            "education", "en", "global", ["animals", "nature", "wildlife", "documentary", "live"]),
    Channel("Classic Arts Showcase", "https://classicarts.akamaized.net/hls/live/1024257/CAS/master.m3u8",
            "entertainment", "en", "usa", ["arts", "classical music", "opera", "ballet", "culture", "live"]),
    Channel("Create TV", "https://create.lls.pbs.org/index.m3u8",
            "lifestyle", "en", "usa", ["cooking", "travel", "diy", "pbs", "lifestyle", "live"]),
    Channel("PBS Kids", "https://livestream.pbskids.org/out/v1/14507d931bbe48a69287e4850e53443c/est.m3u8",
            "kids", "en", "usa", ["kids", "children", "education", "animation", "pbs", "live"]),
    Channel("Doctor Who Classic", "https://aegis-cloudfront-1.tubi.video/7e9ef0f5-4d13-4083-aa3f-9375e652a4c9/playlist.m3u8",
            "entertainment", "en", "usa", ["sci-fi", "doctor who", "british", "series", "entertainment", "live"]),
    Channel("Dateline 24/7", "https://dz59iptwz5rxs.cloudfront.net/live/master.m3u8",
            "entertainment", "en", "usa", ["crime", "true crime", "nbc", "documentary", "live"]),
    Channel("Mythbusters", "https://d1cgf0ptrv4t22.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-xvoparaodgcw9/Mythbusters_GB.m3u8",
            "education", "en", "uk", ["science", "experiments", "discovery", "entertainment", "live"]),
    Channel("FilmRise Classic TV", "https://d2tv4k5moji5m7.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-lu4pzh9l4b57p/master.m3u8",
            "entertainment", "en", "usa", ["classic tv", "retro", "sitcoms", "nostalgia", "live"]),
    Channel("The Archive Classic Movies", "https://cineverse.g-mana.live/media/09899328-5b22-4d3e-ba1e-111856798c99/playlist_3.m3u8",
            "entertainment", "en", "usa", ["movies", "classic movies", "cinema", "retro", "live"]),
    Channel("Comet", "https://fast-channels.sinclairstoryline.com/COMET/index.m3u8",
            "entertainment", "en", "usa", ["sci-fi", "fantasy", "horror", "movies", "series", "live"]),
    Channel("Charge!", "https://fast-channels.sinclairstoryline.com/CHARGE/index.m3u8",
            "entertainment", "en", "usa", ["action", "movies", "crime", "police", "live"]),
    Channel("Grit Xtra", "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01438-ewscrippscompan-gritxtra-tablo/playlist.m3u8",
            "entertainment", "en", "usa", ["western", "action", "classic", "movies", "live"]),
    Channel("ION Plus", "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01438-ewscrippscompan-ionplus-tablo/playlist.m3u8",
            "entertainment", "en", "usa", ["drama", "crime", "procedural", "series", "live"]),
    Channel("Bounce XL", "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01438-ewscrippscompan-bouncexl-tablo/playlist.m3u8",
            "entertainment", "en", "usa", ["movies", "sitcoms", "drama", "african american", "live"]),
    Channel("TVS Comedy Network", "https://rpn.bozztv.com/gusa/gusa-tvscomedy/index.m3u8",
            "entertainment", "en", "usa", ["comedy", "sitcoms", "humor", "stand-up", "live"]),
    Channel("TVS Quiz Show Network", "https://rpn.bozztv.com/gusa/gusa-tvsgameshow/index.m3u8",
            "entertainment", "en", "usa", ["game show", "quiz", "trivia", "entertainment", "live"]),
    Channel("Cloudflare TV", "https://cloudflare.tv/hls/live.m3u8",
            "education", "en", "usa", ["technology", "tech", "security", "engineering", "live"]),
    Channel("Free Speech TV", "https://edge.fstv-live-linear-channel.top.comcast.net/Content/HLS_HLSv3/Live/channel(b168a609-19c1-2203-ae1d-6b9726f05e67)/index.m3u8",
            "news", "en", "usa", ["news", "politics", "progressive", "documentary", "live"]),
    Channel("America's Voice", "https://content.uplynk.com/channel/26bd482ffe364a1282bc3df28bd3c21f.m3u8",
            "news", "en", "usa", ["news", "politics", "conservative", "usa", "live"]),
    Channel("Entertainment Tonight", "https://cbsta49f-cbsta49f-ms.global.ssl.fastly.net/amagi7b98-AmagiMixible/master/amagi7b98-AmagiMixible.m3u8",
            "entertainment", "en", "usa", ["celebrity", "hollywood", "pop culture", "entertainment", "live"]),
    Channel("Yahoo! Finance", "https://d1ewctnvcwvvvu.cloudfront.net/playlist.m3u8",
            "news", "en", "usa", ["finance", "business", "stocks", "economy", "financial", "markets", "bursa", "yahoo", "live"]),
    Channel("World Channel PBS", "https://world.lls.pbs.org/index.m3u8",
            "education", "en", "usa", ["documentary", "pbs", "culture", "history", "science", "live"]),
    Channel("FNX First Nations", "https://fnx.lls.pbs.org/index.m3u8",
            "education", "en", "usa", ["indigenous", "native american", "culture", "documentary", "pbs", "live"]),

    # ── MUSIC ──────────────────────────────────────────────────────────────────
    Channel("Vevo Pop", "https://jmp2.uk/stvp-GBBC19000017V",
            "music", "en", "uk", ["music", "pop", "music videos", "vevo", "hits", "live"]),
    Channel("Vevo Hip Hop", "https://d3mzlmrngyf08j.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-55k4m9whplndi/playlist.m3u8",
            "music", "en", "usa", ["music", "hip hop", "rap", "r&b", "urban", "vevo", "live"]),
    Channel("NEW K-POP", "https://newidco-newkid-1-eu.xiaomi.wurl.tv/playlist.m3u8",
            "music", "ko", "south-korea", ["music", "k-pop", "kpop", "korean", "pop", "live"]),
    Channel("Clubbing TV", "https://d1j2csarxnwazk.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-uze1m6xh4fiyr-ssai-prd/master.m3u8",
            "music", "en", "global", ["music", "edm", "electronic", "dance", "club", "djs", "live"]),
    Channel("Deluxe Music", "https://sdn-global-live-streaming-packager-cache.3qsdn.com/13456/13456_264_live.m3u8",
            "music", "de", "germany", ["music", "pop", "rock", "hits", "german", "live"]),
    Channel("Deluxe Dance", "https://sdn-global-live-streaming-packager-cache.3qsdn.com/64733/64733_264_live.m3u8",
            "music", "de", "germany", ["music", "dance", "edm", "electronic", "house", "german", "live"]),
    Channel("Deluxe Rap", "https://sdn-global-live-streaming-packager-cache.3qsdn.com/65183/65183_264_live.m3u8",
            "music", "de", "germany", ["music", "rap", "hip hop", "trap", "urban", "german", "live"]),
    Channel("Schlager Deluxe", "https://sdn-global-live-streaming-packager-cache.3qsdn.com/26658/26658_264_live.m3u8",
            "music", "de", "germany", ["music", "schlager", "german music", "folk", "live"]),
    Channel("Magenta Musik 360", "https://streaming.magentamusik.de/csm/573870/magentamusik1/index.m3u8",
            "music", "de", "germany", ["music", "concerts", "festivals", "live music", "german", "live"]),
    Channel("ONE1 Music", "https://cdne.folxplay.tv/folx-trz/streams/ch-3/master.m3u8",
            "music", "de", "germany", ["music", "pop", "hits", "charts", "german", "live"]),
    Channel("One Adria", "https://cdne.folxplay.tv/folx-trz/streams/ch-6/master.m3u8",
            "music", "multi", "global", ["music", "pop", "balkan", "adria", "live"]),
    Channel("ZWEI2 Music", "https://cdne.folxplay.tv/folx-trz/streams/ch-2/master.m3u8",
            "music", "de", "germany", ["music", "pop", "dance", "hits", "german", "live"]),
    Channel("Radio 21 TV", "https://live.creacast.com/radio21/smil:radio21.smil/playlist.m3u8",
            "music", "de", "germany", ["music", "rock", "classic rock", "radio", "german", "live"]),
    Channel("SWR 3 Visual Radio", "https://swrswr3vr-hls.akamaized.net/hls/live/2018683/swr3vr/master.m3u8",
            "music", "de", "germany", ["music", "pop", "radio", "german", "live"]),
    Channel("TVM3 Music", "https://livevideo.infomaniak.com/streaming/livecast/tvm3/playlist.m3u8",
            "music", "fr", "switzerland", ["music", "music videos", "pop", "swiss", "french", "live"]),
    Channel("The Country Network", "https://amg00600-amg00600c1-thecountrynetwork-us-5497.playouts.now.amagi.tv/playlist.m3u8",
            "music", "en", "usa", ["country music", "music videos", "american", "live"]),
    Channel("FashionTV Paris", "https://edge-fast3.evrideo.tv/bfdbb576-83f7-11f0-9f89-0200170e3e04_1000028043_HLS/manifest.m3u8",
            "lifestyle", "en", "france", ["fashion", "style", "runway", "paris", "france", "luxury", "live"]),
    Channel("Global Fashion Channel", "https://pubgfc.teleosmedia.com/linear/globalfashionchannel/globalfashionchannel/playlist.m3u8",
            "lifestyle", "en", "global", ["fashion", "style", "modeling", "trends", "beauty", "live"]),

    # ── SPORTS ─────────────────────────────────────────────────────────────────
    Channel("Tennis Channel International", "https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01444-tennischannelth-tennischnlintl-lggb/playlist.m3u8",
            "sports", "en", "global", ["tennis", "sports", "atp", "wta", "tournaments", "live"]),
    Channel("MotoAmerica TV", "https://1422977263.rsc.cdn77.org/HLS/MOTOAMERICA.m3u8",
            "sports", "en", "usa", ["motorcycle racing", "motorsports", "racing", "live"]),
    Channel("Lacrosse TV", "https://1840769862.rsc.cdn77.org/FTF/LSN_SCTE.m3u8",
            "sports", "en", "usa", ["lacrosse", "sports", "college", "live"]),
    Channel("FanDuel TV", "https://d2jl8r92tdc3f1.cloudfront.net/out/v1/59419700344b4625b7cb0693ba265ea3/TVGindex_1.m3u8",
            "sports", "en", "usa", ["sports betting", "horse racing", "racing", "usa", "live"]),
    Channel("FIFA+ English", "https://a62dad94.wurl.com/master/f36d25e7e52f1ba8d7e56eb859c636563214f541/UmFrdXRlblRWLWV1X0ZJRkFQbHVzRW5nbGlzaF9ITFM/playlist.m3u8",
            "sports", "en", "global", ["football", "soccer", "fifa", "world cup", "sports", "live"]),
    Channel("Pursuit Channel", "https://d2qa45tniogkj6.cloudfront.net/out/v1/30f129d3a8a8482b9efe5092cf46e601/index.m3u8",
            "sports", "en", "usa", ["hunting", "fishing", "outdoors", "adventure", "live"]),
    Channel("L'Equipe HD", "https://dshn8inoshngm.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-gac2i63dmu8b7/LEquipe_FR.m3u8",
            "sports", "fr", "france", ["sports", "football", "cycling", "french", "live"]),

    # ── KIDS ───────────────────────────────────────────────────────────────────
    Channel("KiKA", "https://kikahls.akamaized.net/hls/live/2022690/livetvkika_ww/master.m3u8",
            "kids", "de", "germany", ["kids", "children", "cartoons", "animation", "german", "live"]),
    Channel("RiC TV", "https://rictv.iptv-playoutcenter.de/rictv/rictv-web/playlist.m3u8",
            "kids", "de", "germany", ["kids", "children", "cartoons", "animation", "german", "live"]),
    Channel("Nick Germany", "https://0d26a00dfbb1.airspace-cdn.cbsivideo.com/nick1999/master/nick1999.m3u8",
            "kids", "de", "germany", ["kids", "nickelodeon", "cartoons", "animation", "german", "live"]),
    Channel("Lego Channel", "https://jmp2.uk/stvp-GBBC4300005AL",
            "kids", "en", "uk", ["kids", "lego", "animation", "cartoons", "family", "live"]),
    Channel("Caillou", "https://do7nccdsswstc.cloudfront.net/v1/manifest/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-1aso0bc668saa/a5233c83-f772-4a81-959a-45ec7877ef61/5.m3u8",
            "kids", "en", "canada", ["kids", "caillou", "animation", "education", "family", "live"]),
    Channel("RetroCrush Anime", "https://cineverse.g-mana.live/media/ac7cff3c-5bc3-4745-ac4d-56aadb586d00/profile/1/profileManifest.m3u8",
            "entertainment", "en", "usa", ["anime", "classic anime", "retro", "japanese", "live"]),
    Channel("ADN TV Anime", "https://d3b73b34o7cvkq.cloudfront.net/v1/master/3722c60a815c199d9c0ef36c5b73da68a62b09d1/cc-gz2sgqzp076kf/adn.m3u8",
            "entertainment", "fr", "france", ["anime", "french", "animation", "live"]),
    Channel("Toonami Aftermath East", "http://api.toonamiaftermath.com:3000/est/playlist.m3u8",
            "entertainment", "en", "usa", ["anime", "cartoons", "toonami", "retro", "action", "live"]),

    # ── UK ─────────────────────────────────────────────────────────────────────
    Channel("BBC One HD", "https://november.queazified.co.uk/ee971134-115e-4418-8d1d-69dff7d4c6eb.m3u8",
            "entertainment", "en", "uk", ["bbc", "news", "drama", "entertainment", "uk", "british", "live"]),
    Channel("BBC Two HD", "https://viamotionhsi.netplus.ch/live/eds/bbc2/browser-HLS8/bbc2.m3u8",
            "entertainment", "en", "uk", ["bbc", "culture", "documentary", "drama", "uk", "british", "live"]),
    Channel("ITV 2 HD", "https://viamotionhsi.netplus.ch/live/eds/itv2/browser-HLS8/itv2.m3u8",
            "entertainment", "en", "uk", ["itv", "entertainment", "reality tv", "comedy", "uk", "british", "live"]),
    Channel("Channel 4 HD", "https://viamotionhsi.netplus.ch/live/eds/channel4/browser-HLS8/channel4.m3u8",
            "entertainment", "en", "uk", ["channel 4", "entertainment", "drama", "comedy", "documentary", "uk", "british", "live"]),
    Channel("Film4 HD", "https://viamotionhsi.netplus.ch/live/eds/film4/browser-HLS8/film4.m3u8",
            "entertainment", "en", "uk", ["movies", "films", "cinema", "uk", "british", "live"]),
    Channel("BBC America", "https://bcovlive-a.akamaihd.net/7f5ec16d102f4b5d92e8e27bc95ff424/us-east-1/6240731308001/playlist.m3u8",
            "entertainment", "en", "usa", ["bbc", "entertainment", "movies", "series", "british", "live"]),

    # ── FRANCE ─────────────────────────────────────────────────────────────────
    Channel("TF1 HD", "https://viamotionhsi.netplus.ch/live/eds/tf1hd/browser-HLS8/tf1hd.m3u8",
            "entertainment", "fr", "france", ["entertainment", "news", "drama", "series", "france", "french", "live"]),
    Channel("M6 HD", "https://viamotionhsi.netplus.ch/live/eds/m6hd/browser-HLS8/m6hd.m3u8",
            "entertainment", "fr", "france", ["entertainment", "reality tv", "series", "movies", "france", "french", "live"]),
    Channel("France 2 HD", "https://viamotionhsi.netplus.ch/live/eds/france2hd/browser-HLS8/france2hd.m3u8",
            "entertainment", "fr", "france", ["news", "entertainment", "drama", "france", "french", "live"]),
    Channel("France 5 HD", "https://viamotionhsi.netplus.ch/live/eds/france5hd/browser-HLS8/france5hd.m3u8",
            "education", "fr", "france", ["documentary", "education", "culture", "france", "french", "live"]),
    Channel("W9", "https://viamotionhsi.netplus.ch/live/eds/w9/browser-HLS8/w9.m3u8",
            "entertainment", "fr", "france", ["entertainment", "music", "reality tv", "france", "french", "live"]),
    Channel("Game One", "https://viamotionhsi.netplus.ch/live/eds/gameone/browser-HLS8/gameone.m3u8",
            "entertainment", "fr", "france", ["gaming", "video games", "anime", "esports", "france", "french", "live"]),
    Channel("Planete+", "https://viamotionhsi.netplus.ch/live/eds/planeteplus/browser-HLS8/planeteplus.m3u8",
            "education", "fr", "france", ["documentary", "history", "science", "nature", "france", "french", "live"]),
    Channel("Paramount Channel", "https://viamotionhsi.netplus.ch/live/eds/paramount/browser-HLS8/paramount.m3u8",
            "entertainment", "fr", "france", ["movies", "hollywood", "action", "drama", "comedy", "live"]),

    # ── GERMANY ────────────────────────────────────────────────────────────────
    Channel("Das Erste HD", "https://daserste-live.ard-mcdn.de/daserste/live/hls/int/master.m3u8",
            "entertainment", "de", "germany", ["news", "entertainment", "sports", "series", "ard", "german", "live"]),
    Channel("ZDF", "https://zdf-hls-15.akamaized.net/hls/live/2016498/de/high/master.m3u8",
            "entertainment", "de", "germany", ["news", "entertainment", "sports", "zdf", "german", "live"]),
    Channel("ZDFinfo", "https://zdf-hls-17.akamaized.net/hls/live/2016500/de/high/master.m3u8",
            "education", "de", "germany", ["documentary", "history", "science", "politics", "zdf", "german", "live"]),
    Channel("ZDFneo", "https://zdf-hls-16.akamaized.net/hls/live/2016499/de/high/master.m3u8",
            "entertainment", "de", "germany", ["entertainment", "series", "comedy", "movies", "zdf", "german", "live"]),
    Channel("Phoenix", "https://zdf-hls-19.akamaized.net/hls/live/2016502/de/high/master.m3u8",
            "news", "de", "germany", ["news", "politics", "documentaries", "german", "live"]),
    Channel("Tagesschau 24", "https://tagesschau.akamaized.net/hls/live/2020115/tagesschau/tagesschau_1/master.m3u8",
            "news", "de", "germany", ["news", "breaking news", "politics", "ard", "german", "live"]),
    Channel("WDR Fernsehen", "https://wdr-live.ard-mcdn.de/wdr/live/hls/de/master.m3u8",
            "entertainment", "de", "germany", ["local news", "culture", "entertainment", "wdr", "german", "nrw", "live"]),
    Channel("RBB Berlin", "https://rbb-hls-berlin.akamaized.net/hls/live/2017824/rbb_berlin/index.m3u8",
            "entertainment", "de", "germany", ["local news", "berlin", "rbb", "german", "live"]),
    Channel("NDR Hamburg", "https://mcdn.ndr.de/ndr/hls/ndr_fs/ndr_hh/master.m3u8",
            "entertainment", "de", "germany", ["local news", "hamburg", "ndr", "german", "live"]),
    Channel("BR Fernsehen Nord", "https://mcdn.br.de/br/fs/bfs_nord/hls/de/master.m3u8",
            "entertainment", "de", "germany", ["local news", "bavaria", "br", "german", "live"]),
    Channel("TV Berlin", "https://live2.telvi.de/hls/tvberlin.m3u8",
            "news", "de", "germany", ["local news", "berlin", "german", "live"]),
    Channel("Hamburg 1", "https://stream.hamburg1.de/live_abr/hamburg1_abr/playlist.m3u8",
            "entertainment", "de", "germany", ["local news", "hamburg", "german", "live"]),
    Channel("Welt der Wunder TV", "https://wdw.iptv-playoutcenter.de/wdw/wdw1/playlist.m3u8",
            "education", "de", "germany", ["documentary", "science", "technology", "nature", "german", "live"]),
    Channel("Sky Cinema Family HD", "https://d17lsiabqrlwa2.cloudfront.net/pl_138/207480-6535776-1/playlist.m3u8",
            "kids", "de", "germany", ["movies", "family", "kids", "animation", "german", "live"]),
    Channel("Bibel TV", "https://bibint01.iptv-playoutcenter.de/bibint01/bibint01.stream_all/playlist.m3u8",
            "religious", "de", "germany", ["christian", "religion", "faith", "german", "live"]),

    # ── SWITZERLAND ────────────────────────────────────────────────────────────
    Channel("SRF 1 HD", "https://viamotionhsi.netplus.ch/live/eds/srf1hd/browser-HLS8/srf1hd.m3u8",
            "entertainment", "de", "switzerland", ["news", "entertainment", "swiss", "german", "live"]),
    Channel("SRF zwei HD", "https://viamotionhsi.netplus.ch/live/eds/srf2hd/browser-HLS8/srf2hd.m3u8",
            "sports", "de", "switzerland", ["sports", "movies", "entertainment", "swiss", "german", "live"]),
    Channel("SRF info HD", "https://viamotionhsi.netplus.ch/live/eds/srfinfo/browser-HLS8/srfinfo.m3u8",
            "news", "de", "switzerland", ["news", "current affairs", "swiss", "german", "live"]),
    Channel("RTS 1 HD", "https://viamotionhsi.netplus.ch/live/eds/rts1hd/browser-HLS8/rts1hd.m3u8",
            "entertainment", "fr", "switzerland", ["news", "entertainment", "swiss", "french", "live"]),
    Channel("TeleZüri", "https://cdnapisec.kaltura.com/p/1719221/sp/171922100/playManifest/entryId/1_se36k3uk/protocol/https/format/applehttp/flavorIds/1_i4zc9zv3,1_2vzxm8zl,1_yjohpwzj/a.m3u8",
            "news", "de", "switzerland", ["local news", "zurich", "swiss", "german", "live"]),
    Channel("TV 24 HD", "https://viamotionhsi.netplus.ch/live/eds/tv24/browser-HLS8/tv24.m3u8",
            "entertainment", "de", "switzerland", ["entertainment", "movies", "swiss", "german", "live"]),

    # ── RELIGIOUS ──────────────────────────────────────────────────────────────
    Channel("TBN", "https://d7ge95bb03xsu.cloudfront.net/out/v1/0c95a89614194912834019fc37d741ef/tbn-freecast.m3u8",
            "religious", "en", "usa", ["christian", "faith", "gospel", "sermons", "religious", "live"]),
    Channel("CBN", "https://fastly.live.brightcove.com/6380396819112/us-east-1/734546207001/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiczFpM3ZpLmVncmVzcy50N2M3emwiLCJhY2NvdW50X2lkIjoiNzM0NTQ2MjA3MDAxIiwiZWhuIjoiZmFzdGx5LmxpdmUuYnJpZ2h0Y292ZS5jb20iLCJpc3OiOiJibGl2ZS1wbGF5YmFjay1zb3VyY2UtYXBpIiwic3ViIjoicGF0aG1hcHRva2VuIiwiYXVkIjpbIjczNDU0NjIwNzAwMSJdLCJqdGkiOiI2MzgwMzk2ODE5MTEyIn0.GDYp4IWtzwPkupEWeeOavnioVknO-Ev3UGlHvM1rE6I/playlist-hls.m3u8",
            "religious", "en", "usa", ["christian", "faith", "gospel", "news", "religious", "live"]),
    Channel("Catholic TV", "https://catholictvhd-lh.akamaized.net/hls/live/2043390/CTVLiveHD/master.m3u8",
            "religious", "en", "usa", ["catholic", "christian", "faith", "mass", "religious", "live"]),
    Channel("Hope Channel North America", "https://jstre.am/live/jsl:0sUSK6VA7GT.m3u8",
            "religious", "en", "usa", ["christian", "adventist", "faith", "religious", "live"]),
    Channel("Shalom World", "https://broadcaster-1.cclouds.in/srt-2/channel2_abr/playlist.m3u8",
            "religious", "en", "usa", ["catholic", "christian", "faith", "religious", "live"]),

    # ── SHOPPING ───────────────────────────────────────────────────────────────
    Channel("HSN", "https://qvc-amd-live.akamaized.net/hls/live/2034113/lshsn1us/master.m3u8",
            "shopping", "en", "usa", ["shopping", "deals", "fashion", "jewelry", "hsn", "live"]),
    Channel("QVC 3", "https://qvc-amd-live.akamaized.net/hls/live/2034113/lsqvc3us/master.m3u8",
            "shopping", "en", "usa", ["shopping", "deals", "fashion", "qvc", "live"]),
    Channel("QVC Germany", "https://qvcde-live.akamaized.net/hls/live/2097104/qvc/master.m3u8",
            "shopping", "de", "germany", ["shopping", "deals", "fashion", "qvc", "german", "live"]),
    Channel("Jewelry Television", "https://content.jwplatform.com/live/broadcast/oe7UD7Ag.m3u8",
            "shopping", "en", "usa", ["shopping", "jewelry", "gems", "retail", "live"]),
    Channel("Shop LC", "https://cdn-shop-lc-01.akamaized.net/Content/HLS_HLS/Live/channel(ott)/master.m3u8",
            "shopping", "en", "usa", ["shopping", "jewelry", "fashion", "deals", "live"]),
    Channel("HSE 24", "https://hse24.akamaized.net/hls/live/2006663/hse24/playlist.m3u8",
            "shopping", "de", "germany", ["shopping", "fashion", "beauty", "german", "live"]),

    # ── MIDDLE EAST / ARABIC ───────────────────────────────────────────────────
    Channel("Alhurra TV", "https://mbn-ingest-worldsafe.akamaized.net/hls/live/2038900/MBN_Alhurra_Worldsafe_HLS/master.m3u8",
            "news", "ar", "usa", ["news", "arabic", "middle east", "usa", "live"]),
    Channel("SBC Saudi Broadcasting", "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-sbc/90e09c0c28db26435799b4a14892a167/index.m3u8",
            "entertainment", "ar", "saudi-arabia", ["news", "culture", "arabic", "saudi arabia", "live"]),
    Channel("Al Saudiya", "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-saudi-tv/2ad66056b51fd8c1b624854623112e43/index.m3u8",
            "entertainment", "ar", "saudi-arabia", ["news", "culture", "arabic", "saudi arabia", "live"]),
]


# ── Stopwords & High-Priority Domain Keywords ────────────────────────────────

STOP_WORDS = {
    "a", "an", "the", "and", "or", "with", "for", "to", "of", "in", "on", "at",
    "i", "want", "watch", "open", "play", "show", "find", "channel",
    "dua", "hap", "shiko", "kanal", "nje", "një", "me", "dhe", "ose", "per", "për"
}

FINANCE_KEYWORDS = {
    "finance", "financial", "markets", "market", "stocks", "stock", "economy",
    "business", "bursa", "financa", "tregjet", "tregu"
}


# ── Helper functions ──────────────────────────────────────────────────────────

def get_channel(name: str):
    name_lower = name.strip().lower()
    for ch in CHANNELS:
        if ch.name.lower() == name_lower:
            return _to_dict(ch)
    return None


def find_best_channel(query: str):
    query_lower = query.lower().strip()
    words = [w for w in query_lower.split() if len(w) >= 2 and w not in STOP_WORDS]
    best, best_score = None, 0

    for ch in CHANNELS:
        score = 0
        name_lower = ch.name.lower()
        tags = [t.lower() for t in (ch.tags or [])]
        category_lower = (ch.category or "").lower()

        # 1. Përputhje e plotë ose me nënvarg te emri i kanalit
        if query_lower == name_lower:
            score += 20
        elif query_lower in name_lower:
            score += 10
        elif any(len(w) >= 3 and w in name_lower for w in words):
            score += 4

        # 2. Përputhje te kategoria
        if category_lower and category_lower in words:
            score += 4

        # 3. Përputhje e fjalëve te etiketat (tags)
        for w in words:
            if w in tags:
                score += 8 if w in FINANCE_KEYWORDS else 4
            elif len(w) >= 4 and any(w in t for t in tags):
                score += 2

        if score > best_score:
            best_score = score
            best = ch

    return _to_dict(best) if best else None


def search_channels_by_tag(keyword: str):
    keyword = keyword.lower()
    return [_to_dict(ch) for ch in CHANNELS
            if ch.tags and any(keyword in tag for tag in ch.tags)]


def get_channels_by_category(category: str):
    category = category.lower()
    return [_to_dict(ch) for ch in CHANNELS if ch.category == category]


def get_news_channels():
    return get_channels_by_category("news")


def get_music_channels():
    return get_channels_by_category("music")


def get_sports_channels():
    return get_channels_by_category("sports")


def get_kids_channels():
    return get_channels_by_category("kids")


def get_albanian_channels():
    return [_to_dict(ch) for ch in CHANNELS
            if ch.tags and ("albanian" in ch.tags or "kosovo" in ch.tags or "albania" in ch.tags)]


def get_balkan_channels():
    return [_to_dict(ch) for ch in CHANNELS
            if ch.tags and "balkans" in ch.tags]


def _to_dict(ch: Channel):
    return {
        "name": ch.name,
        "url": ch.url,
        "category": ch.category,
        "language": ch.language,
        "country": ch.country,
        "tags": ch.tags,
        "is_live": ch.is_live,
    }
