import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from scipy.spatial import KDTree
import io
from streamlit_drawable_canvas import st_canvas

# 設定網頁標題為寬螢幕模式
st.set_page_config(page_title="8mm 實體積木拼豆編輯器", layout="wide")
st.title("🎨 8mm 實體積木拼豆編輯器 (雲端穩定版)")
st.write("左側自由塗抹，右側自動執行「嚴格方格對齊」與即時數量統計。")

# --- 🎨 數位增豔版：27 色實體積木調色盤 (微調深色系抓取範圍) ---
BEAD_PALETTE = {
    "黑色": (0, 0, 0), "深灰色": (70, 70, 70), "淺灰色": (200, 200, 200),
    "白色": (255, 255, 255), "透明透白": (240, 248, 255),
    "正紅色": (255, 0, 0), "桃紅色": (255, 0, 127), "淺粉色": (255, 192, 203),
    "紫紅色": (200, 0, 150), "亮橘色": (255, 165, 0), "正橘色": (255, 69, 0),
    "金黃色": (255, 215, 0), "正黃色": (255, 255, 0), "淺黃色": (255, 255, 180),
    "膚色": (255, 218, 185), "奶油色": (255, 253, 208), "棕色": (165, 42, 42),
    "深棕色": (101, 67, 33), "淺綠色": (50, 255, 50), "正綠色": (0, 200, 0),
    "深綠色": (0, 100, 0), "湖水藍": (0, 255, 255), "淺藍色": (0, 191, 255),
    "天藍色": (0, 127, 255), "正藍色": (0, 0, 255), 
    "深藍色": (30, 40, 100), # 🌟 微調：更容易抓住小丑原圖偏灰暗的藍色衣服
    "紫色": (148, 0, 211)
}

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

color_names = list(BEAD_PALETTE.keys())
color_values = list(BEAD_PALETTE.values())
kdtree = KDTree(color_values)

if 'canvas_key_id' not in st.session_state:
    st.session_state.canvas_key_id = 0
if 'base_img' not in st.session_state:
    st.session_state.base_img = None
if 'current_file_id' not in st.session_state:
    st.session_state.current_file_id = ""

# === 🌟 核心退回：「原圖銳利取點 (NEAREST)」 ===
def process_to_beads(image, grid_size):
    img_rgb = image.convert('RGB')
    width, height = img_rgb.size
    cols = grid_size
    rows = int(height * grid_size / width)
    
    # 不做色彩平均，保持原圖邊緣銳利度
    tiny_img = img_rgb.resize((cols, rows), Image.Resampling.NEAREST)
    tiny_pixels = tiny_img.load()
    
    base_img = Image.new('RGB', (cols, rows))
    pixels = base_img.load()
    
    for r in range(rows):
        for c in range(cols):
            raw_rgb = tiny_pixels[c, r]
            _, index = kdtree.query(raw_rgb)
            pixels[c, r] = color_values[index]
            
    return base_img, cols, rows

def draw_preview_template(img, cols, rows, grid_thickness, peg_dot_size, scale_factor=20):
    final_w = cols * scale_factor
    final_h = rows * scale_factor
    template_img = img.resize((final_w, final_h), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(template_img)
    cell_w = final_w / cols
    cell_h = final_h / rows
    for r in range(rows):
        for c in range(cols):
            rect = [c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h]
            if grid_thickness > 0:
                draw.rectangle(rect, outline=(180, 180, 180), width=grid_thickness)
            if peg_dot_size > 0:
                dot_r = peg_dot_size / 2
                dot_center = [(c + 0.5) * cell_w, (r + 0.5) * cell_h]
                dot_rect = [dot_center[0]-dot_r, dot_center[1]-dot_r, dot_center[0]+dot_r, dot_center[1]+dot_r]
                draw.ellipse(dot_rect, fill=(210, 210, 210))
    return template_img

st.sidebar.header("1. 轉換設定")
grid_size = st.sidebar.slider("格板寬度 (格數)", 10, 120, 30)

st.sidebar.header("2. 畫筆設定")
selected_color_name = st.sidebar.selectbox("🎨 選擇替換顏色", color_names)
brush_color_rgb = BEAD_PALETTE[selected_color_name]
brush_hex_color = rgb_to_hex(brush_color_rgb)

st.sidebar.header("3. 匯出顯示設定")
grid_thickness = st.sidebar.slider("方格線粗細", 0, 5, 1)
peg_dot_size = st.sidebar.slider("中心凸點大小", 0, 10, 2)

uploaded_file = st.file_uploader("上傳原始圖片 (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    file_id = f"{uploaded_file.name}_{uploaded_file.size}_{grid_size}"
    if st.session_state.current_file_id != file_id:
        original_image = Image.open(uploaded_file)
        base_pixel_img, cols, rows = process_to_beads(original_image, grid_size)
        st.session_state.base_img = base_pixel_img
        st.session_state.current_file_id = file_id
        st.session_state.canvas_key_id = 0 
        st.session_state.cols = cols
        st.session_state.rows = rows
    
    cols = st.session_state.cols
    rows = st.session_state.rows

    canvas_scale = 18 
    canvas_w = cols * canvas_scale
    canvas_h = rows * canvas_scale
    
    bg_image = st.session_state.base_img.resize((canvas_w, canvas_h), Image.Resampling.NEAREST)
    draw_bg = ImageDraw.Draw(bg_image)
    for r in range(rows):
        for c in range(cols):
            rect = [c * canvas_scale, r * canvas_scale, (c + 1) * canvas_scale, (r + 1) * canvas_scale]
            draw_bg.rectangle(rect, outline=(200, 200, 200), width=1)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖌️ 左側：自由塗抹區")
        canvas_result = st_canvas(
            fill_color=brush_hex_color,
            stroke_width=canvas_scale * 0.8, 
            stroke_color=brush_hex_color,
            background_image=bg_image,
            update_streamlit=True,
            height=canvas_h,
            width=canvas_w,
            drawing_mode="freedraw",
            key=f"stable_canvas_{st.session_state.canvas_key_id}",
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 將左側塗鴉合併到底圖並清空畫布", use_container_width=True):
            st.session_state.base_img = st.session_state.current_snapped_img
            st.session_state.canvas_key_id += 1
            st.rerun()

    with col2:
        st.subheader("✨ 右側：完美對齊預覽")
        current_preview_img = st.session_state.base_img.copy()
        pixels = current_preview_img.load()
        
        if canvas_result.image_data is not None:
            drawn_data = canvas_result.image_data
            for r in range(rows):
                for c in range(cols):
                    patch = drawn_data[r*canvas_scale:(r+1)*canvas_scale, c*canvas_scale:(c+1)*canvas_scale]
                    alphas = patch[:, :, 3]
                    if np.any(alphas > 50): 
                        max_alpha_idx = np.argmax(alphas)
                        flat_patch = patch.reshape(-1, 4)
                        drawn_r, drawn_g, drawn_b = flat_patch[max_alpha_idx][:3]
                        _, idx = kdtree.query((drawn_r, drawn_g, drawn_b))
                        pixels[c, r] = color_values[idx]
        
        st.session_state.current_snapped_img = current_preview_img
        preview_display = draw_preview_template(current_preview_img, cols, rows, grid_thickness, peg_dot_size, scale_factor=canvas_scale)
        st.image(preview_display, use_column_width=True)

    st.markdown("---")
    final_export_img = draw_preview_template(st.session_state.current_snapped_img, cols, rows, grid_thickness, peg_dot_size, scale_factor=20)
    
    buf = io.BytesIO()
    final_export_img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    st.download_button(label="📥 下載最終確認版拼豆底圖", data=byte_im, file_name="bead_template.png", mime="image/png")
    
    unique, counts = np.unique(np.array(st.session_state.current_snapped_img).reshape(-1, 3), axis=0, return_counts=True)
    st.write("**當前實際所需數量：**")
    for color, count in zip(unique, counts):
        for name, val in BEAD_PALETTE.items():
            if val == tuple(color):
                st.write(f"- {name}: **{count}** 顆")
