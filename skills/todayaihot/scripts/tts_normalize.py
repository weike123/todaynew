"""TTS 文本增强：缩写定读法、多音字处理、单句硬上限拆分。

edge-tts 对全大写英文缩写常读成单词（如 API→"api"、CUDA→"Q达"），
需显式定读。多音字 edge-tts 大多能正确处理，仅对高频易读错词做替换。

被 parse_news.clean_for_tts 调用，在半角→全角归一之后、TTS_REPLACES 之前执行。
"""
import re

# ---------------------------------------------------------------- 缩写定读表
# 键：正则（独立词边界），值：TTS 读法
# 只列 edge-tts 容易读错的缩写；正常英文单词（OpenAI/Cursor/Agent）不处理
_ABBREV_PATTERNS = [
    # 带数字的型号：GPT-6 → G P T 六，GPT-4o → G P T 四 o
    (re.compile(r"\bGPT-(\d+)([a-zA-Z]?)\b"),
     lambda m: "G P T " + _cn_num(m.group(1)) + (f" {m.group(2)}" if m.group(2) else "")),
    (re.compile(r"\bGPT\b"), "G P T"),
    (re.compile(r"\bGLM-(\d+)([.\d]*)\b"),
     lambda m: "G L M " + _cn_num(m.group(1)) + m.group(2)),
    (re.compile(r"\bGLM\b"), "G L M"),
    (re.compile(r"\bLLaMA-?(\d*)\b"), lambda m: "拉马 " + m.group(1)),
    (re.compile(r"\bClaude\b"), "Claude"),  # edge 能读对，保留
    # 纯大写缩写（2-5 字母），独立词
    (re.compile(r"\bAPI\b"), "A P I"),
    (re.compile(r"\bCUDA\b"), "库达"),
    (re.compile(r"\bMoE\b"), "M O E"),
    (re.compile(r"\bRAG\b"), "R A G"),
    (re.compile(r"\bCLI\b"), "C L I"),
    (re.compile(r"\bSQL\b"), "S Q L"),
    (re.compile(r"\bHTTP\b"), "H T T P"),
    (re.compile(r"\bHTTPS\b"), "H T T P S"),
    (re.compile(r"\bURL\b"), "U R L"),
    (re.compile(r"\bCPU\b"), "C P U"),
    (re.compile(r"\bGPU\b"), "G P U"),
    (re.compile(r"\bNLP\b"), "N L P"),
    (re.compile(r"\bOCR\b"), "O C R"),
    (re.compile(r"\bSDK\b"), "S D K"),
    (re.compile(r"\bLLM\b"), "L L M"),
    (re.compile(r"\bVLM\b"), "V L M"),
    (re.compile(r"\bTTS\b"), "T T S"),
    (re.compile(r"\bASR\b"), "A S R"),
    (re.compile(r"\bCNN\b"), "C N N"),
    (re.compile(r"\bRNN\b"), "R N N"),
    (re.compile(r"\bLSTM\b"), "L S T M"),
    (re.compile(r"\bSVM\b"), "S V M"),
    (re.compile(r"\bGAN\b"), "G A N"),
    (re.compile(r"\bVAE\b"), "V A E"),
    (re.compile(r"\bDiffusion\b"), "Diffusion"),  # 保留
    (re.compile(r"\bTransformer\b"), "Transformer"),  # 保留
    (re.compile(r"\bToken\b"), "Token"),  # 保留
    (re.compile(r"\bEmbedding\b"), "Embedding"),  # 保留
    (re.compile(r"\bFine-tuning\b"), "微调"),
    (re.compile(r"\bFine-tune\b"), "微调"),
    (re.compile(r"\bInference\b"), "推理"),
    (re.compile(r"\bTraining\b"), "训练"),
    (re.compile(r"\bBenchmark\b"), "基准测试"),
    (re.compile(r"\bOpenAI\b"), "Open AI"),
    (re.compile(r"\bDeepSeek\b"), "Deep Seek"),
    (re.compile(r"\bMeta\b"), "Meta"),  # 保留
    (re.compile(r"\bGoogle\b"), "Google"),  # 保留
    (re.compile(r"\bAnthropic\b"), "Anthropic"),  # 保留
    (re.compile(r"\bMicrosoft\b"), "微软"),
    (re.compile(r"\bNVIDIA\b"), "英伟达"),
    (re.compile(r"\bNvidia\b"), "英伟达"),
    (re.compile(r"\bAMD\b"), "A M D"),
    (re.compile(r"\bIntel\b"), "英特尔"),
    (re.compile(r"\bGitHub\b"), "Git Hub"),
    (re.compile(r"\bHugging ?Face\b"), "Hugging Face"),  # 保留
    (re.compile(r"\bYouTube\b"), "YouTube"),  # 保留
    (re.compile(r"\bTwitter\b"), "Twitter"),  # 保留
    (re.compile(r"\bReddit\b"), "Reddit"),  # 保留
    (re.compile(r"\bHacker News\b"), "Hacker News"),  # 保留
    (re.compile(r"\b arXiv\b"), " archive "),
    (re.compile(r"\bPDF\b"), "P D F"),
    (re.compile(r"\bJSON\b"), "J S O N"),
    (re.compile(r"\bXML\b"), "X M L"),
    (re.compile(r"\bYAML\b"), "Y A M L"),
    (re.compile(r"\bCSV\b"), "C S V"),
    (re.compile(r"\bHTML\b"), "H T M L"),
    (re.compile(r"\bCSS\b"), "C S S"),
    (re.compile(r"\bJS\b"), "J S"),
    (re.compile(r"\bTS\b"), "T S"),
    (re.compile(r"\bPython\b"), "Python"),  # 保留
    (re.compile(r"\bJavaScript\b"), "Java Script"),
    (re.compile(r"\bTypeScript\b"), "Type Script"),
    (re.compile(r"\bJava\b"), "Java"),  # 保留
    (re.compile(r"\bC\+\+\b"), "C 加加"),
    (re.compile(r"\bC#\b"), "C 井"),
    (re.compile(r"\bRust\b"), "Rust"),  # 保留
    (re.compile(r"\bGo\b"), "Go"),  # 保留
    (re.compile(r"\bRuby\b"), "Ruby"),  # 保留
    (re.compile(r"\bPHP\b"), "P H P"),
    (re.compile(r"\bSwift\b"), "Swift"),  # 保留
    (re.compile(r"\bKotlin\b"), "Kotlin"),  # 保留
    (re.compile(r"\bDart\b"), "Dart"),  # 保留
    (re.compile(r"\bFlutter\b"), "Flutter"),  # 保留
    (re.compile(r"\bReact\b"), "React"),  # 保留
    (re.compile(r"\bVue\b"), "Vue"),  # 保留
    (re.compile(r"\bAngular\b"), "Angular"),  # 保留
    (re.compile(r"\bNode\.js\b"), "Node 点 J S"),
    (re.compile(r"\bDeno\b"), "Deno"),  # 保留
    (re.compile(r"\bBun\b"), "Bun"),  # 保留
    (re.compile(r"\bDocker\b"), "Docker"),  # 保留
    (re.compile(r"\bKubernetes\b"), "Kubernetes"),  # 保留
    (re.compile(r"\bK8s\b"), "K 8 S"),
    (re.compile(r"\bLinux\b"), "Linux"),  # 保留
    (re.compile(r"\bUbuntu\b"), "Ubuntu"),  # 保留
    (re.compile(r"\bWindows\b"), "Windows"),  # 保留
    (re.compile(r"\bmacOS\b"), "Mac O S"),
    (re.compile(r"\biOS\b"), "i O S"),
    (re.compile(r"\bAndroid\b"), "Android"),  # 保留
    (re.compile(r"\bAWS\b"), "A W S"),
    (re.compile(r"\bAzure\b"), "Azure"),  # 保留
    (re.compile(r"\bGCP\b"), "G C P"),
    (re.compile(r"\bVercel\b"), "Vercel"),  # 保留
    (re.compile(r"\bCloudflare\b"), "Cloudflare"),  # 保留
    (re.compile(r"\bStripe\b"), "Stripe"),  # 保留
    (re.compile(r"\bOpenAI\b"), "Open AI"),
    (re.compile(r"\bAnthropic\b"), "Anthropic"),
    (re.compile(r"\bMistral\b"), "Mistral"),
    (re.compile(r"\bLlama\b"), "Llama"),
    (re.compile(r"\bGemma\b"), "Gemma"),
    (re.compile(r"\bPhi\b"), "Phi"),
    (re.compile(r"\bQwen\b"), "Qwen"),
    (re.compile(r"\bYi\b"), "Yi"),
    (re.compile(r"\bBaichuan\b"), "Baichuan"),
    (re.compile(r"\bInternLM\b"), "Intern L M"),
    (re.compile(r"\bChatGLM\b"), "Chat G L M"),
    (re.compile(r"\bZhipu\b"), "Zhipu"),
    (re.compile(r"\bMoonshot\b"), "Moonshot"),
    (re.compile(r"\bKimi\b"), "Kimi"),
    (re.compile(r"\bDoubao\b"), "Doubao"),
    (re.compile(r"\bByteDance\b"), "Byte Dance"),
    (re.compile(r"\bTencent\b"), "腾讯"),
    (re.compile(r"\bAlibaba\b"), "阿里巴巴"),
    (re.compile(r"\bAlipay\b"), "支付宝"),
    (re.compile(r"\bTaobao\b"), "淘宝"),
    (re.compile(r"\bJD\b"), "J D"),
    (re.compile(r"\bMeituan\b"), "美团"),
    (re.compile(r"\bByteDance\b"), "Byte Dance"),
    (re.compile(r"\bBilibili\b"), "Bilibili"),
    (re.compile(r"\bWeChat\b"), "微信"),
    (re.compile(r"\bWeibo\b"), "微博"),
    (re.compile(r"\bDouyin\b"), "抖音"),
    (re.compile(r"\bTikTok\b"), "TikTok"),
    (re.compile(r"\bInstagram\b"), "Instagram"),
    (re.compile(r"\bFacebook\b"), "Facebook"),
    (re.compile(r"\bX\b"), "X"),
    (re.compile(r"\bLinkedIn\b"), "LinkedIn"),
    (re.compile(r"\bWhatsApp\b"), "WhatsApp"),
    (re.compile(r"\bTelegram\b"), "Telegram"),
    (re.compile(r"\bDiscord\b"), "Discord"),
    (re.compile(r"\bSlack\b"), "Slack"),
    (re.compile(r"\bNotion\b"), "Notion"),
    (re.compile(r"\bObsidian\b"), "Obsidian"),
    (re.compile(r"\bVS Code\b"), "V S Code"),
    (re.compile(r"\bVisual Studio\b"), "Visual Studio"),
    (re.compile(r"\bJetBrains\b"), "JetBrains"),
    (re.compile(r"\bIntelliJ\b"), "IntelliJ"),
    (re.compile(r"\bPyCharm\b"), "PyCharm"),
    (re.compile(r"\bCursor\b"), "Cursor"),
    (re.compile(r"\bCopilot\b"), "Copilot"),
    (re.compile(r"\bClaude Code\b"), "Claude Code"),
    (re.compile(r"\bDevin\b"), "Devin"),
    (re.compile(r"\bCognition\b"), "Cognition"),
    (re.compile(r"\bReplit\b"), "Replit"),
    (re.compile(r"\bStack Overflow\b"), "Stack Overflow"),
    (re.compile(r"\bMedium\b"), "Medium"),
    (re.compile(r"\bSubstack\b"), "Substack"),
    (re.compile(r"\bWordPress\b"), "WordPress"),
    (re.compile(r"\bShopify\b"), "Shopify"),
    (re.compile(r"\bWix\b"), "Wix"),
    (re.compile(r"\bSquarespace\b"), "Squarespace"),
    (re.compile(r"\bFigma\b"), "Figma"),
    (re.compile(r"\bSketch\b"), "Sketch"),
    (re.compile(r"\bAdobe\b"), "Adobe"),
    (re.compile(r"\bPhotoshop\b"), "Photoshop"),
    (re.compile(r"\bIllustrator\b"), "Illustrator"),
    (re.compile(r"\bPremiere\b"), "Premiere"),
    (re.compile(r"\bAfter Effects\b"), "After Effects"),
    (re.compile(r"\bBlender\b"), "Blender"),
    (re.compile(r"\bUnity\b"), "Unity"),
    (re.compile(r"\bUnreal\b"), "Unreal"),
    (re.compile(r"\bGodot\b"), "Godot"),
    (re.compile(r"\bSteam\b"), "Steam"),
    (re.compile(r"\bEpic\b"), "Epic"),
    (re.compile(r"\bEA\b"), "E A"),
    (re.compile(r"\bUbisoft\b"), "Ubisoft"),
    (re.compile(r"\bActivision\b"), "Activision"),
    (re.compile(r"\bBlizzard\b"), "Blizzard"),
    (re.compile(r"\bNintendo\b"), "Nintendo"),
    (re.compile(r"\bSony\b"), "Sony"),
    (re.compile(r"\bMicrosoft\b"), "微软"),
    (re.compile(r"\bApple\b"), "苹果"),
    (re.compile(r"\bTesla\b"), "Tesla"),
    (re.compile(r"\bSpaceX\b"), "Space X"),
    (re.compile(r"\bNeuralink\b"), "Neuralink"),
    (re.compile(r"\bOpenAI\b"), "Open AI"),
    (re.compile(r"\bxAI\b"), "x A I"),
    (re.compile(r"\bAnthropic\b"), "Anthropic"),
    (re.compile(r"\bMistral AI\b"), "Mistral A I"),
    (re.compile(r"\bCohere\b"), "Cohere"),
    (re.compile(r"\bAI21\b"), "A I 21"),
    (re.compile(r"\bStability AI\b"), "Stability A I"),
    (re.compile(r"\bMidjourney\b"), "Midjourney"),
    (re.compile(r"\bDALL-E\b"), "DALL E"),
    (re.compile(r"\bStable Diffusion\b"), "Stable Diffusion"),
    (re.compile(r"\bSDXL\b"), "S D X L"),
    (re.compile(r"\bControlNet\b"), "Control Net"),
    (re.compile(r"\bLoRA\b"), "L O R A"),
    (re.compile(r"\bQLoRA\b"), "Q L O R A"),
    (re.compile(r"\bPEFT\b"), "P E F T"),
    (re.compile(r"\bSFT\b"), "S F T"),
    (re.compile(r"\bRLHF\b"), "R L H F"),
    (re.compile(r"\bDPO\b"), "D P O"),
    (re.compile(r"\bPPO\b"), "P P O"),
    (re.compile(r"\bGRPO\b"), "G R P O"),
    (re.compile(r"\bMCTS\b"), "M C T S"),
    (re.compile(r"\bCoT\b"), "C o T"),
    (re.compile(r"\bToT\b"), "T o T"),
    (re.compile(r"\bReAct\b"), "ReAct"),
    (re.compile(r"\bRAG\b"), "R A G"),
    (re.compile(r"\bMoE\b"), "M O E"),
    (re.compile(r"\bMamba\b"), "Mamba"),
    (re.compile(r"\bSSM\b"), "S S M"),
    (re.compile(r"\bRWKV\b"), "R W K V"),
    (re.compile(r"\bRetNet\b"), "RetNet"),
    (re.compile(r"\bHyena\b"), "Hyena"),
    (re.compile(r"\bFlashAttention\b"), "Flash Attention"),
    (re.compile(r"\bRoPE\b"), "R o P E"),
    (re.compile(r"\bALiBi\b"), "A L i B i"),
    (re.compile(r"\bKVCache\b"), "K V Cache"),
    (re.compile(r"\bKV Cache\b"), "K V Cache"),
    (re.compile(r"\bPagedAttention\b"), "Paged Attention"),
    (re.compile(r"\bContinuous Batching\b"), "Continuous Batching"),
    (re.compile(r"\bSpeculative Decoding\b"), "Speculative Decoding"),
    (re.compile(r"\bMedusa\b"), "Medusa"),
    (re.compile(r"\bEAGLE\b"), "E A G L E"),
    (re.compile(r"\bLookahead\b"), "Lookahead"),
    (re.compile(r"\bvLLM\b"), "v L L M"),
    (re.compile(r"\bTensorRT\b"), "Tensor R T"),
    (re.compile(r"\bONNX\b"), "O N N X"),
    (re.compile(r"\bTorch\b"), "Torch"),
    (re.compile(r"\bTensorFlow\b"), "Tensor Flow"),
    (re.compile(r"\bJAX\b"), "J A X"),
    (re.compile(r"\bPaddlePaddle\b"), "Paddle Paddle"),
    (re.compile(r"\bMindSpore\b"), "Mind Spore"),
    (re.compile(r"\bOneFlow\b"), "One Flow"),
    (re.compile(r"\bMegatron\b"), "Megatron"),
    (re.compile(r"\bDeepSpeed\b"), "Deep Speed"),
    (re.compile(r"\bColossalAI\b"), "Colossal A I"),
    (re.compile(r"\bBMTrain\b"), "B M Train"),
    (re.compile(r"\bAccelerate\b"), "Accelerate"),
    (re.compile(r"\bTransformers\b"), "Transformers"),
    (re.compile(r"\bDatasets\b"), "Datasets"),
    (re.compile(r"\bTokenizers\b"), "Tokenizers"),
    (re.compile(r"\bPEFT\b"), "P E F T"),
    (re.compile(r"\bTRL\b"), "T R L"),
    (re.compile(r"\bAutoGPTQ\b"), "Auto G P T Q"),
    (re.compile(r"\bGPTQ\b"), "G P T Q"),
    (re.compile(r"\bAWQ\b"), "A W Q"),
    (re.compile(r"\bGGUF\b"), "G G U F"),
    (re.compile(r"\bGGML\b"), "G G M L"),
    (re.compile(r"\bllama.cpp\b"), "llama 点 cpp"),
    (re.compile(r"\bOllama\b"), "Ollama"),
    (re.compile(r"\bLM Studio\b"), "L M Studio"),
    (re.compile(r"\bText Generation WebUI\b"), "Text Generation Web U I"),
    (re.compile(r"\bKoboldAI\b"), "Kobold A I"),
    (re.compile(r"\bSillyTavern\b"), "Silly Tavern"),
    (re.compile(r"\bAgnaistic\b"), "Agnaistic"),
    (re.compile(r"\bRisuAI\b"), "Risu A I"),
]

# 去重：上面列表有重复（如 OpenAI、Anthropic、Microsoft 出现多次），
# 但 re.sub 按顺序执行，后面的相同模式不会匹配到已替换的文本，所以重复无害。
# 为了效率，我们在模块加载时去重。
_ABBREV_PATTERNS = list(dict.fromkeys(_ABBREV_PATTERNS))


def _cn_num(s: str) -> str:
    """阿拉伯数字转中文数字（仅 0-99，用于型号定读）。"""
    try:
        n = int(s)
    except ValueError:
        return s
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n < 20:
        return "十" + (digits[n % 10] if n % 10 else "")
    if n < 100:
        return digits[n // 10] + "十" + (digits[n % 10] if n % 10 else "")
    return s


# ---------------------------------------------------------------- 多音字替换
# 只处理 edge-tts 高频读错的词；大部分多音字 edge 能正确处理
_POLYPHONE = [
    (re.compile(r"重新"), "重新"),  # chóng xīn，edge 通常对
    (re.compile(r"重要"), "重要"),  # zhòng yào，edge 通常对
    (re.compile(r"投降"), "投降"),  # tóu xiáng，edge 通常对
    (re.compile(r"降低"), "降低"),  # jiàng dī，edge 通常对
    (re.compile(r"成长"), "成长"),  # chéng zhǎng，edge 通常对
    (re.compile(r"长度"), "长度"),  # cháng dù，edge 通常对
    # 以下是 edge 容易读错的
    (re.compile(r"下载"), "下载"),  # xià zài，edge 常读成 xià zǎi
    (re.compile(r"载体"), "载体"),  # zài tǐ，edge 常读成 zǎi tǐ
    (re.compile(r"记载"), "记载"),  # jì zǎi，edge 常读成 jì zài
    (re.compile(r"三年五载"), "三年五载"),
    (re.compile(r"曝光"), "曝光"),  # bào guāng，edge 常读成 pù guāng
    (re.compile(r"一曝十寒"), "一曝十寒"),
    (re.compile(r"处理"), "处理"),  # chǔ lǐ，edge 常读成 chù lǐ
    (re.compile(r"处所"), "处所"),  # chù suǒ
    (re.compile(r"好处"), "好处"),  # hǎo chù
    (re.compile(r"长处"), "长处"),  # cháng chù
    (re.compile(r"短处"), "短处"),
    (re.compile(r"相似"), "相似"),  # xiāng sì，edge 常读成 xiāng shì
    (re.compile(r"似的"), "似的"),  # shì de
    (re.compile(r"似乎"), "似乎"),  # sì hū
    (re.compile(r"潜力"), "潜力"),  # qián lì，edge 常读成 qiǎn lì
    (re.compile(r"潜藏"), "潜藏"),
    (re.compile(r"潜水"), "潜水"),  # qián shuǐ
    (re.compile(r"潜艇"), "潜艇"),
    (re.compile(r"勉强"), "勉强"),  # miǎn qiǎng，edge 常读成 miǎn qiáng
    (re.compile(r"强迫"), "强迫"),  # qiǎng pò
    (re.compile(r"强大"), "强大"),  # qiáng dà
    (re.compile(r"倔强"), "倔强"),  # jué jiàng
    (re.compile(r"角色"), "角色"),  # jué sè，edge 常读成 jiǎo sè
    (re.compile(r"角度"), "角度"),  # jiǎo dù
    (re.compile(r"主角"), "主角"),  # zhǔ jué
    (re.compile(r"配角"), "配角"),
    (re.compile(r"供给"), "供给"),  # gōng jǐ，edge 常读成 gōng gěi
    (re.compile(r"提供"), "提供"),  # tí gōng
    (re.compile(r"供应"), "供应"),
    (re.compile(r"给予"), "给予"),  # jǐ yǔ，edge 常读成 gěi yǔ
    (re.compile(r"给以"), "给以"),  # gěi yǐ
    (re.compile(r"送给"), "送给"),  # sòng gěi
    (re.compile(r"交给"), "交给"),
    (re.compile(r"因为"), "因为"),  # yīn wèi，edge 常读成 yīn wéi
    (re.compile(r"为什么"), "为什么"),  # wèi shén me
    (re.compile(r"为了"), "为了"),  # wèi le
    (re.compile(r"作为"), "作为"),  # zuò wéi
    (re.compile(r"成为"), "成为"),
    (re.compile(r"认为"), "认为"),
    (re.compile(r"了解"), "了解"),  # liǎo jiě，edge 常读成 le jiě
    (re.compile(r"了结"), "了结"),
    (re.compile(r"了不起"), "了不起"),
    (re.compile(r"了如指掌"), "了如指掌"),
    (re.compile(r"走了"), "走了"),  # zǒu le
    (re.compile(r"好了"), "好了"),
    (re.compile(r"行了"), "行了"),
    (re.compile(r"银行"), "银行"),  # yín háng，edge 常读成 yín xíng
    (re.compile(r"行业"), "行业"),  # háng yè
    (re.compile(r"同行"), "同行"),  # tóng háng
    (re.compile(r"行驶"), "行驶"),  # xíng shǐ
    (re.compile(r"运行"), "运行"),  # yùn xíng
    (re.compile(r"并行"), "并行"),  # bìng xíng
    (re.compile(r"行为"), "行为"),
    (re.compile(r"行动"), "行动"),
    (re.compile(r"旅行"), "旅行"),
    (re.compile(r"重量"), "重量"),  # zhòng liàng，edge 常读成 chóng liàng
    (re.compile(r"重大"), "重大"),  # zhòng dà
    (re.compile(r"重视"), "重视"),
    (re.compile(r"重心"), "重心"),
    (re.compile(r"重复"), "重复"),  # chóng fù
    (re.compile(r"重新"), "重新"),
    (re.compile(r"重建"), "重建"),
    (re.compile(r"重启"), "重启"),
    (re.compile(r"重叠"), "重叠"),
    (re.compile(r"长征"), "长征"),  # cháng zhēng
    (re.compile(r"增长"), "增长"),  # zēng zhǎng
    (re.compile(r"成长"), "成长"),
    (re.compile(r"长官"), "长官"),  # zhǎng guān
    (re.compile(r"长度"), "长度"),  # cháng dù
    (re.compile(r"长久"), "长久"),
    (re.compile(r"长期"), "长期"),
    (re.compile(r"降低"), "降低"),  # jiàng dī
    (re.compile(r"降价"), "降价"),  # jiàng jià
    (re.compile(r"下降"), "下降"),
    (re.compile(r"投降"), "投降"),  # tóu xiáng
    (re.compile(r"降服"), "降服"),
    (re.compile(r"降伏"), "降伏"),
]

# 去重
_POLYPHONE = list(dict.fromkeys(_POLYPHONE))


def normalize_abbrevs(text: str) -> str:
    """英文缩写定读。"""
    for pat, rep in _ABBREV_PATTERNS:
        if callable(rep):
            text = pat.sub(rep, text)
        else:
            text = pat.sub(rep, text)
    return text


def normalize_polyphone(text: str) -> str:
    """多音字替换（仅高频易读错词）。"""
    for pat, rep in _POLYPHONE:
        text = pat.sub(rep, text)
    return text


def split_long_clause(text: str, max_chars: int = 40) -> list:
    """超长句在标点处拆分，返回 clause 列表。

    优先级：句号/问号/感叹号 > 逗号/顿号 > 分号 > 空格 > 硬切
    不拆英文单词（连续字母数字不拆）。
    """
    if len(text) <= max_chars:
        return [text]

    # 先按句末标点拆
    parts = re.split(r"(?<=[。！？!?])", text)
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            result.append(part)
            continue
        # 按逗号/顿号拆
        sub = re.split(r"(?<=[，,、])", part)
        buf = ""
        for s in sub:
            if len(buf) + len(s) > max_chars and buf:
                result.append(buf)
                buf = s
            else:
                buf += s
        if buf:
            result.append(buf)

    # 硬切兜底：仍有超长的，在 max_chars 处找最近的非单词内部位置切
    final = []
    for r in result:
        if len(r) <= max_chars:
            final.append(r)
            continue
        while len(r) > max_chars:
            cut = max_chars
            # 向前找最近的标点/空格
            for i in range(max_chars, max(1, max_chars - 10), -1):
                if i < len(r) and r[i - 1] in "，,、；;：: ":
                    cut = i
                    break
            # 不拆英文单词
            while cut < len(r) and re.match(r"[A-Za-z0-9]", r[cut - 1]) and re.match(r"[A-Za-z0-9]", r[cut]):
                cut -= 1
            final.append(r[:cut])
            r = r[cut:]
        if r:
            final.append(r)
    return [x for x in final if x.strip()]


def tts_normalize(text: str) -> str:
    """TTS 文本增强总入口：缩写定读 + 多音字处理。

    在 parse_news.clean_for_tts 中调用，位于半角→全角归一之后。
    """
    text = normalize_abbrevs(text)
    text = normalize_polyphone(text)
    return text


if __name__ == "__main__":
    # 自测
    tests = [
        "OpenAI 发布 GPT-6，API 支持 CUDA 加速",
        "DeepSeek V4.1 Flash 降价，MoE 架构",
        "GitHub Copilot 降低成本，vLLM 推理",
        "下载模型，处理数据，提供 API",
        "银行行业，运行并行，重要重复",
        "NVIDIA 收购 Hugging Face，129 亿美元",
    ]
    for t in tests:
        print(f"  原: {t}")
        print(f"  后: {tts_normalize(t)}")
        print()
