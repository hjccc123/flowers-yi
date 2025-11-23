import streamlit as st
import random
import json
import os
from datetime import datetime

# --- 1. 基础配置与数据加载 ---

# 设置页面标题和图标
st.set_page_config(
    page_title="梅花易数 & 金钱卦",
    page_icon="☯️",
    layout="centered"
)

# 隐藏默认菜单和页脚
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 定义常量
LINE_YANG = "——"
LINE_YIN = "-- --"

# 八卦基础信息 (先天数序: 1乾 2兑 3离 4震 5巽 6坎 7艮 8坤)
# 映射到三爻的二进制 (Bottom, Middle, Top) 1=Yang, 0=Yin
BAGUA_MAP = {
    1: {"name": "乾", "bits": (1, 1, 1)},
    2: {"name": "兑", "bits": (1, 1, 0)},
    3: {"name": "离", "bits": (1, 0, 1)},
    4: {"name": "震", "bits": (1, 0, 0)},
    5: {"name": "巽", "bits": (0, 1, 1)},
    6: {"name": "坎", "bits": (0, 1, 0)},
    7: {"name": "艮", "bits": (0, 0, 1)},
    8: {"name": "坤", "bits": (0, 0, 0)},
}
# 反向映射
TRIGRAMS = {v["bits"]: v["name"] for k, v in BAGUA_MAP.items()}

# 加载易经数据
@st.cache_data
def load_yijing_data():
    # 尝试读取本地数据
    try:
        with open("data/yijing_cn.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("未找到易经数据文件 (data/yijing_cn.json)")
        return {}

YIJING = load_yijing_data()

# --- 2. 核心逻辑函数 ---

def coin_throw_line(rng):
    """金钱卦模拟：三枚铜钱"""
    coins = [rng.choice([2, 3]) for _ in range(3)]
    s = sum(coins)
    # 6=老阴(动), 7=少阳, 8=少阴, 9=老阳(动)
    is_yang = True if s in (7, 9) else False
    is_moving = s in (6, 9)
    display = LINE_YANG if is_yang else LINE_YIN
    return {"sum": s, "is_yang": is_yang, "is_moving": is_moving, "display": display}

def build_line_from_bit(bit, is_moving):
    """根据 阴阳(0/1) 和 是否动爻 构建线数据"""
    if bit == 1:
        s = 9 if is_moving else 7
    else:
        s = 6 if is_moving else 8
    
    display = LINE_YANG if bit == 1 else LINE_YIN
    return {"sum": s, "is_yang": bit == 1, "is_moving": is_moving, "display": display}

def generate_hexagram(method, params=None):
    """生成卦象核心逻辑"""
    lines = []
    
    # --- 1. 金钱卦 ---
    if method == "coins":
        rng = random.SystemRandom()
        lines = [coin_throw_line(rng) for _ in range(6)]

    # --- 2. 数字卦 & 3. 年月日时卦 ---
    elif method in ["numbers", "datetime"]:
        upper_val = 0
        lower_val = 0
        moving_rem = 0
        
        if method == "numbers":
            n1 = int(params.get("num1", 0))
            n2 = int(params.get("num2", 0))
            
            upper_val = n1 % 8 or 8
            lower_val = n2 % 8 or 8
            moving_rem = (n1 + n2) % 6 or 6
            
        elif method == "datetime":
            y = int(params.get("year", 0))
            m = int(params.get("month", 0))
            d = int(params.get("day", 0))
            h = int(params.get("hour", 0))
            
            sum_date = y + m + d
            sum_all = sum_date + h
            
            upper_val = sum_date % 8 or 8
            lower_val = sum_all % 8 or 8
            moving_rem = sum_all % 6 or 6

        # 梅花易数：上卦在上(索引3-5)，下卦在下(索引0-2)
        lower_bits = BAGUA_MAP[lower_val]["bits"]
        upper_bits = BAGUA_MAP[upper_val]["bits"]
        
        all_bits = list(lower_bits) + list(upper_bits)
        moving_idx = moving_rem - 1
        
        lines = []
        for i in range(6):
            is_moving = (i == moving_idx)
            lines.append(build_line_from_bit(all_bits[i], is_moving))

    # --- 通用结果处理 ---
    primary_bits = [1 if ln["is_yang"] else 0 for ln in lines]
    moving_indexes = [i for i, ln in enumerate(lines) if ln["is_moving"]]

    result_bits = primary_bits.copy()
    for i, ln in enumerate(lines):
        if ln["is_moving"]:
            result_bits[i] = 1 - result_bits[i]

    def bits_key(bits): return "".join(str(b) for b in bits)
    
    gua_db = YIJING.get("gua_by_bits", {})
    primary_gua = gua_db.get(bits_key(primary_bits))
    result_gua = gua_db.get(bits_key(result_bits))

    def get_trigram_name(bits_slice):
        # tuple 转换
        t = tuple(bits_slice) 
        # 我们的 BAGUA_MAP bits 是 (bottom, middle, top)
        # 切片后 [0:3] 是 [bot, mid, top]
        # 所以直接查
        return TRIGRAMS.get(t, "?")

    return {
        "lines": lines,
        "primary_bits": primary_bits,
        "result_bits": result_bits,
        "moving_indexes": moving_indexes,
        "primary_gua": primary_gua,
        "result_gua": result_gua,
        "lower_trigram": get_trigram_name(primary_bits[0:3]),
        "upper_trigram": get_trigram_name(primary_bits[3:6]),
    }

def gather_yao_texts(gua, moving_indexes):
    if not gua: return []
    yaos = []
    yao_dict = gua.get("yao", {})
    # JSON 中 key 是 "1".."6"
    # moving_indexes 是 0..5
    for i in range(6):
        pos = i + 1
        text = yao_dict.get(str(pos), "")
        yaos.append({"pos": pos, "text": text, "is_moving": i in moving_indexes})
    return yaos

def smart_interpretation(primary_gua, result_gua, moving_indexes, primary_yaos):
    hints = []
    num_moving = len(moving_indexes)
    if not primary_gua: return ["未找到主卦数据。"]
    
    p_name = primary_gua.get("name", "主卦")
    r_name = result_gua.get("name", "变卦") if result_gua else "变卦"

    if num_moving == 0:
        hints.append(f"**【静卦】** 本卦无动爻。")
        hints.append(f"💡 **断法**：请直接参考 **{p_name}** 的卦辞。")
        hints.append(f"> *{primary_gua.get('gua_ci', '')}*")
    elif num_moving == 1:
        idx = moving_indexes[0]
        yao_pos = idx + 1
        moving_yao_text = next((y['text'] for y in primary_yaos if y['pos'] == yao_pos), "")
        hints.append(f"**【一爻动】** 动爻在第 {yao_pos} 爻。")
        hints.append(f"💡 **断法**：事情的变数就在这一爻上，重点研读。")
        hints.append(f"> *{moving_yao_text}*")
        if result_gua:
            hints.append(f"📈 **趋势**：变卦为 **{r_name}**，代表事情的终局或趋势。")
    elif num_moving > 1:
        hints.append(f"**【多爻动】** 有 {num_moving} 个动爻，局面复杂。")
        if result_gua:
            hints.append(f"💡 **断法**：因为变数多，**变卦({r_name})** 的权重极大，代表最终不可逆转的走向。")
            hints.append(f"> *变卦卦辞：{result_gua.get('gua_ci', '')}*")
            
    return hints

# --- 3. 界面显示逻辑 ---

st.title("☯️ 梅花易数 & 金钱卦")

# 侧边栏/顶部输入区
with st.container():
    question = st.text_input("问事（可选）", placeholder="诚心而占，输入问题...")
    
    method_options = {
        "coins": "金钱卦（模拟摇铜钱）",
        "numbers": "数字卦（两个数起卦）",
        "datetime": "年月日时起卦（梅花先天）"
    }
    method = st.selectbox("起卦方式", options=list(method_options.keys()), format_func=lambda x: method_options[x])
    
    params = {}
    
    if method == "coins":
        st.info("系统将使用真随机数模拟抛掷六次三枚铜钱。")
        
    elif method == "numbers":
        col1, col2 = st.columns(2)
        with col1:
            params["num1"] = st.number_input("第一个数 (上卦)", min_value=1, step=1, value=8, help="例如随意报出的第一个数，或书页码等")
        with col2:
            params["num2"] = st.number_input("第二个数 (下卦)", min_value=1, step=1, value=16, help="例如随意报出的第二个数")
        st.caption("规则：数1除8余数为上卦，数2除8余数为下卦，两数和除6余数为动爻。")
        
    elif method == "datetime":
        st.caption("请输入农历时间或您心中的“时间数”：")
        c1, c2 = st.columns(2)
        with c1:
            params["year"] = st.number_input("年 (地支数)", min_value=1, max_value=12, value=5, help="子1 丑2 ... 辰5 ... 亥12")
            params["day"] = st.number_input("农历日", min_value=1, max_value=30, value=15)
        with c2:
            params["month"] = st.number_input("农历月", min_value=1, max_value=12, value=3)
            params["hour"] = st.number_input("时 (地支数)", min_value=1, max_value=12, value=8, help="子1 丑2 ... 未8 ... 亥12")
        st.caption("地支参考：子1 丑2 寅3 卯4 辰5 巳6 午7 未8 申9 酉10 戌11 亥12")

    start_btn = st.button("开始起卦", type="primary", use_container_width=True)

# 结果显示区
if start_btn:
    st.divider()
    
    # 1. 生成结果
    res = generate_hexagram(method, params)
    
    # 2. 准备数据
    p_bits = res["primary_bits"]
    r_bits = res["result_bits"]
    mov_idx = set(res["moving_indexes"])
    chg_idx = set(i for i in range(6) if p_bits[i] != r_bits[i])
    
    # 3. 显示卦象 (六线)
    # Streamlit 不方便做复杂的 CSS 叠加，我们用两列展示文本或简单的图
    
    st.subheader("起卦结果")
    if question:
        st.write(f"**问：** {question}")
        
    col_p, col_r = st.columns(2)
    
    # 辅助函数：渲染六爻 HTML
    def render_hexagram_html(bits, moving_indices=None, changed_indices=None, title=""):
        html = f"<div style='text-align:center; background:#f9f9f9; padding:10px; border-radius:8px;'>"
        html += f"<h4 style='margin:0 0 10px 0;'>{title}</h4>"
        
        # bits 是从下到上，显示要从上到下 (reversed)
        # 也就是索引 5 -> 0
        for i in range(5, -1, -1):
            bit = bits[i]
            # 样式逻辑
            line_str = LINE_YANG if bit==1 else LINE_YIN
            color = "#333"
            bg = "transparent"
            border = "none"
            extra_info = ""
            
            # 检查是否是动爻/变爻
            is_moving = moving_indices and (i in moving_indices)
            is_changed = changed_indices and (i in changed_indices)
            
            if is_moving:
                bg = "#fff4e5" # 浅橙色背景
                extra_info = "<span style='font-size:10px; color:#f59e0b; margin-left:5px;'>●动</span>"
            if is_changed and not is_moving: # 仅在变卦中标记“变”
                bg = "#ebf8ff"
                extra_info = "<span style='font-size:10px; color:#3b82f6; margin-left:5px;'>变</span>"
            
            # 行容器
            html += f"<div style='font-family:monospace; font-size:22px; line-height:1.5; background:{bg}; border-radius:4px;'>{line_str}{extra_info}</div>"
        
        html += "</div>"
        return html

    with col_p:
        p_html = render_hexagram_html(p_bits, moving_indices=mov_idx, title="主卦 (本)")
        st.markdown(p_html, unsafe_allow_html=True)
        if res['primary_gua']:
            st.markdown(f"**{res['primary_gua']['name']}**")
            st.caption(f"上{res['upper_trigram']} 下{res['lower_trigram']}")
    
    with col_r:
        if mov_idx:
            r_html = render_hexagram_html(r_bits, changed_indices=chg_idx, title="变卦 (之)")
            st.markdown(r_html, unsafe_allow_html=True)
            if res['result_gua']:
                st.markdown(f"**{res['result_gua']['name']}**")
        else:
            st.info("无动爻，主卦即终卦")

    # 4. 智能断卦提示
    st.divider()
    st.subheader("💡 智能断卦参考")
    
    p_yaos = gather_yao_texts(res["primary_gua"], res["moving_indexes"])
    interpretation = smart_interpretation(res["primary_gua"], res["result_gua"], res["moving_indexes"], p_yaos)
    
    for hint in interpretation:
        st.markdown(hint)

    # 5. 详细卦辞折叠区
    with st.expander("查看详细卦辞与爻辞"):
        if res['primary_gua']:
            st.markdown(f"### 主卦：{res['primary_gua']['name']}")
            st.write(res['primary_gua']['gua_ci'])
            st.markdown("#### 爻辞：")
            for yao in reversed(p_yaos): # 从上到下显示
                prefix = "🔴 " if yao['is_moving'] else ""
                style = "**" if yao['is_moving'] else ""
                st.markdown(f"{prefix}{style}第 {yao['pos']} 爻：{yao['text']}{style}")
        
        if mov_idx and res['result_gua']:
            st.divider()
            st.markdown(f"### 变卦：{res['result_gua']['name']}")
            st.write(res['result_gua']['gua_ci'])
            st.caption("（变卦爻辞通常不作为主要断语，故省略）")