import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from scipy.spatial import KDTree
import io
from streamlit_drawable_canvas import st_canvas

# 設定網頁標題為寬螢幕模式 (方便左右對照)
st.set_page_config(page_title="8mm 嚴格方格拼豆編輯器", layout="wide")
st.title("🎨 8mm 嚴格方格拼豆編輯器")
st.write("左側為原圖對照。請在右側畫布直接點擊或滑動方格，程式會自動為你「整格對齊」填充顏色，不怕畫筆偏掉！")

# --- 27 種實體拼豆調色盤 ---
BEAD_PALETTE = {
    # 無彩色系
    "黑色": (0, 0, 0), 
    "深灰色": (80, 80, 80), 
    "淺灰色": (180, 180, 180),
    "白色": (255, 255, 255), 
    "透明透白": (245, 245, 245), # 稍微偏離純白，讓程式能區分透明色
    
    # 紅粉色系
    "正紅色": (220, 20, 20), 
    "桃紅色": (255, 20, 147), 
    "淺粉色": (255, 182, 193), 
    "紫紅色": (180, 30, 120),
    
    # 黃橘色系
    "亮橘色": (255, 140, 0), 
    "正橘色": (255, 100, 0), 
    "金黃色": (255, 180, 0), 
    "正黃色": (255, 230, 0), 
    "淺黃色": (255, 255, 150),
    
    # 大地與膚色
    "膚色": (255, 200, 160), 
    "奶油色": (255, 240, 200), 
    "棕色": (150, 75, 0), 
    "深棕色": (70, 40, 20),
    
    # 綠色系
    "淺綠色": (144, 238, 144), 
    "正綠色": (0, 180, 50), 
    "深綠色": (0, 100, 0), 
    "湖水藍": (0, 200, 200),
    
    # 藍紫色系
    "淺藍色": (135, 206, 235), 
    "天藍色": (0, 150, 255), 
    "正藍色": (0, 50, 200), 
    "深藍色": (0, 0, 100), 
    "紫色": (128, 0, 128)
}

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

color_names = list(BEAD_PALETTE.keys())
color_values = list(BEAD_PALETTE.values())
kdtree = KDTree(color_values)

# --- 核心轉換：將原圖轉為基礎方格數據 ---
def process_to_beads(image, grid_size):
    img_rgb = image.convert('RGB')
    width, height = img_rgb.size
    cols = grid_size
    rows = int(height * grid_size / width)
    
    base_img = Image.new('RGB', (cols, rows))
    pixels = base_img.load()
    
    peg_w = width / cols
    peg_h = height / rows
    for r in range(rows):
        for c in range(cols):
            center_x = int((c + 0.5) * peg_w)
            center_y = int((r + 0.5) * peg_h)
            raw_rgb = img_rgb.getpixel((center_x, center_y))
            distance, index = kdtree.query(raw_rgb)
            pixels[c, r] = color_values[index]
            
    return base_img, cols, rows

# --- 產生最終列印版底圖 ---
def draw_final_template(img, cols, rows, grid_thickness, peg_dot_size):
    final_w = cols * 20
    final_h = rows * 20
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

# --- 側邊欄控制項 ---
st.sidebar.header("1. 轉換設定")
grid_size = st.sidebar.slider("格板寬度 (格數)", 10, 120, 30)

st.sidebar.header("2. 點擊編輯器設定")
selected_color_name = st.sidebar.selectbox("🎨 選擇替換顏色", color_names)
brush_hex_color = rgb_to_hex(BEAD_PALETTE[selected_color_name])

st.sidebar.header("3. 匯出設定")
grid_thickness = st.sidebar.slider("方格線粗細", 0, 5, 1)
peg_dot_size = st.sidebar.slider("中心凸點大小", 0, 10, 2)

uploaded_file = st.file_uploader("上傳原始圖片 (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    base_pixel_img, cols, rows = process_to_beads(original_image, grid_size)
    
    # 計算畫布大小，讓每一格足夠大 (20 pixel 一格)，方便點擊
    canvas_scale = 20
    canvas_w = cols * canvas_scale
    canvas_h = rows * canvas_scale
    
    # 建立帶有淺色輔助線的畫布背景，讓你知道格子的邊界
    bg_image = base_pixel_img.resize((canvas_w, canvas_h), Image.Resampling.NEAREST)
    draw_bg = ImageDraw.Draw(bg_image)
    for r in range(rows):
        for c in range(cols):
            rect = [c * canvas_scale, r * canvas_scale, (c + 1) * canvas_scale, (r + 1) * canvas_scale]
            draw_bg.rectangle(rect, outline=(220, 220, 220), width=1)

    # 左右排版：左邊原圖，右邊編輯器
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖼️ 原始圖片")
        st.image(original_image, use_column_width=True)
        
    with col2:
        st.subheader("🖱️ 點擊方格編輯區")
        st.write("直接在格子點擊 (或按住滑過)，放開滑鼠後即會「自動對齊」整格填滿！")
        
        # 啟動畫布 (設定筆刷大小幾乎等於方格大小，方便一次塗滿)
        canvas_result = st_canvas(
            fill_color=brush_hex_color,
            stroke_width=canvas_scale * 0.8, 
            stroke_color=brush_hex_color,
            background_image=bg_image,
            update_streamlit=True,
            height=canvas_h,
            width=canvas_w,
            drawing_mode="freedraw",
            key="canvas",
        )

    st.markdown("---")
    st.subheader("✨ 最終專業對位底圖與清單")

    # 核心演算法：絕對方格鎖定 (Grid-Snapping)
    if canvas_result.image_data is not None:
        edited_grid_img = base_pixel_img.copy()
        pixels = edited_grid_img.load()
        drawn_data = canvas_result.image_data
        
        # 將畫布切成一格一格來檢查
        for r in range(rows):
            for c in range(cols):
                y_start = r * canvas_scale
                y_end = (r + 1) * canvas_scale
                x_start = c * canvas_scale
                x_end = (c + 1) * canvas_scale
                
                # 取得這一格裡面的所有像素
                patch = drawn_data[y_start:y_end, x_start:x_end]
                
                # 只要這格裡面有被畫筆沾到一點點 (Alpha 通道判斷)
                alphas = patch[:, :, 3]
                if np.any(alphas > 128):
                    # 取出塗鴉的顏色，強制對應到我們的 27 色，然後覆蓋「整格」
                    colored_pixels = patch[alphas > 128]
                    drawn_r, drawn_g, drawn_b = colored_pixels[0][:3]
                    dist, idx = kdtree.query((drawn_r, drawn_g, drawn_b))
                    pixels[c, r] = color_values[idx]

        # 將處理好、完美方格化的影像繪製成最終格式
        export_img = draw_final_template(edited_grid_img, cols, rows, grid_thickness, peg_dot_size)
        
        # 顯示最終成果與下載
        st.image(export_img, width=800)
        
        buf = io.BytesIO()
        export_img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="📥 確認無誤，下載最終拼豆底圖",
            data=byte_im,
            file_name="perfect_bead_template.png",
            mime="image/png"
        )
        
        # 重新計算實際所需數量
        unique, counts = np.unique(np.array(edited_grid_img).reshape(-1, 3), axis=0, return_counts=True)
        st.write("**修改後實際所需數量：**")
        for color, count in zip(unique, counts):
            # 從 RGB 反查顏色名稱
            for name, val in BEAD_PALETTE.items():
                if val == tuple(color):
                    st.write(f"- {name}: **{count}** 顆")
                    
