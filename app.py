import streamlit as st
import pandas as pd
import re
import google.generativeai as genai

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
# Lệnh này phải được gọi đầu tiên để thiết lập tiêu đề và layout cho trang
st.set_page_config(page_title="Công Cụ Tra Cứu Lốp Xe", layout="wide")

# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data # Decorator giúp lưu kết quả xử lý dữ liệu, tăng tốc độ cho những lần chạy sau
def load_tire_data():
    """
    Hàm này có nhiệm vụ tải và xử lý dữ liệu lốp từ các file CSV.
    """
    try:
        # Đọc file CSV với kiểu dữ liệu là 'str' (văn bản) để tránh lỗi
        df_prices_raw = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG.csv', dtype=str)

        # 1. XỬ LÝ BẢNG GIÁ
        price_cols = ['stt', 'quy_cach', 'ma_gai', 'gia_ban_le']
        num_price_cols = min(len(df_prices_raw.columns), len(price_cols))
        df_prices = df_prices_raw.iloc[:, :num_price_cols]
        df_prices.columns = price_cols[:num_price_cols]
        
        if 'gia_ban_le' in df_prices.columns:
            df_prices['gia_ban_le'] = pd.to_numeric(
                df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), 
                errors='coerce'
            )
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)

        # 2. XỬ LÝ MÔ TẢ MÃ GAI
        magai_cols = ['ma_gai', 'nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']
        num_magai_cols = min(len(df_magai_raw.columns), len(magai_cols))
        df_magai = df_magai_raw.iloc[:, :num_magai_cols]
        df_magai.columns = magai_cols[:num_magai_cols]
        
        # 3. KẾT HỢP CÁC BẢNG DỮ LIỆU
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền các giá trị còn trống
        for col in ['nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']:
            if col not in df_master.columns:
                df_master[col] = 'Chưa có thông tin'
            df_master[col] = df_master[col].fillna('Chưa có thông tin')

        # Làm sạch khoảng trắng thừa
        for col in df_master.columns:
             if df_master[col].dtype == 'object':
                df_master[col] = df_master[col].str.strip()
        
        return df_master

    except FileNotFoundError as e:
        st.error(f"Lỗi không tìm thấy file: **{e.filename}**. Vui lòng kiểm tra lại tên file.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc file: {e}")
        return pd.DataFrame()


# --- PHẦN 3: KHỞI TẠO VÀ CHẠY ỨNG DỤNG ---
df_master = load_tire_data()

# --- Giao diện chính ---
st.title("️🚗 BỘ CÔNG CỤ TRA CỨU LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

# Thanh bên để nhập API Key
with st.sidebar:
    st.header("Cấu hình AI (Tùy chọn)")
    st.markdown("Để bật tính năng viết bài giới thiệu, hãy lấy API Key của bạn từ [Google AI Studio](https://aistudio.google.com/app/apikey) và dán vào đây.")
    google_api_key = st.text_input("Google AI Studio API Key", type="password", key="api_key_input")
    if google_api_key:
        try:
            genai.configure(api_key=google_api_key)
            st.session_state.api_configured = True
            st.success("Đã kết nối với Google AI!")
        except Exception as e:
            st.session_state.api_configured = False
            st.error("API Key không hợp lệ hoặc có lỗi.")

if 'api_configured' not in st.session_state:
    st.session_state.api_configured = False

if df_master.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại thông báo lỗi ở trên.")
else:
    # Giao diện được tối giản, chỉ còn 2 Tab
    tab_search, tab_cost = st.tabs([
        "**🔍 Tra Cứu Lốp Theo Size**", 
        "**🧮 Tính Chi Phí Lốp**"
    ])

    # --- Công cụ 1: Tra cứu giá theo size ---
    with tab_search:
        st.header("Tra cứu lốp Linglong theo kích thước")
        
        size_query = st.text_input(
            "Nhập kích thước lốp bạn muốn tìm:", 
            placeholder="Ví dụ: 215/55R17 hoặc 185R14C"
        )

        if size_query: # Tự động tìm kiếm khi người dùng nhập
            search_term = size_query.strip()
            # Tìm kiếm gần đúng và sắp xếp theo giá
            results = df_master[df_master['quy_cach'].str.contains(search_term, case=False, na=False)]
            
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
            
            # SỬA LỖI: Chỉ gửi 1 yêu cầu AI duy nhất cho tất cả kết quả
            ai_descriptions = {}
            if st.session_state.api_configured and not results.empty:
                with st.expander("📝 **AI Viết Bài Giới Thiệu (Nhấn để xem)**", expanded=True):
                    try:
                        # Tạo một prompt gộp cho tất cả sản phẩm
                        full_prompt = "Với vai trò là một chuyên gia marketing cho hãng lốp Linglong, hãy viết một đoạn giới thiệu sản phẩm ngắn gọn (khoảng 3-4 câu) cho từng sản phẩm dưới đây. Mỗi sản phẩm cách nhau bởi dấu '---'.\n\n"
                        for index, row in results.iterrows():
                            full_prompt += (
                                f"Sản phẩm: Lốp Linglong, size {row['quy_cach']}, mã gai {row['ma_gai']}.\n"
                                f"Thông tin thêm: Ưu điểm là '{row['uu_diem_cot_loi']}'. Phù hợp cho '{row['ung_dung_cu_the']}'.\n\n"
                            )
                        
                        # THAY ĐỔI: Sử dụng model gemini-1.5-pro-latest để có kết quả mạnh mẽ hơn
                        model = genai.GenerativeModel('gemini-1.5-pro-latest')
                        with st.spinner("AI đang sáng tạo nội dung cho tất cả sản phẩm..."):
                            response = model.generate_content(full_prompt)
                            # Tách các mô tả ra
                            descriptions = response.text.split('---')
                            if len(descriptions) == len(results):
                                ai_descriptions = {results.iloc[i]['ma_gai']: desc.strip() for i, desc in enumerate(descriptions)}
                            else:
                                # Nếu AI không trả về đúng số lượng, hiển thị toàn bộ phản hồi
                                ai_descriptions['general'] = response.text
                    except Exception as e:
                        st.error(f"Lỗi khi gọi AI: {e}")

            st.subheader(f"Kết quả tra cứu cho \"{search_term}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                
                # Hiển thị kết quả
                for index, row in results.iterrows():
                    price_str = f"{row['gia_ban_le']:,} VNĐ" if pd.notna(row['gia_ban_le']) else "Chưa có giá"
                    
                    col_title, col_price = st.columns([3, 1])
                    with col_title:
                        st.markdown(f"#### {row['quy_cach']} / {row['ma_gai']}")
                    with col_price:
                        st.markdown(f"<div style='text-align: right; font-size: 1.2em; color: #28a745; font-weight: bold;'>{price_str}</div>", unsafe_allow_html=True)

                    # Hiển thị mô tả từ AI hoặc thông tin cơ bản
                    if ai_descriptions:
                        desc = ai_descriptions.get(row['ma_gai'], ai_descriptions.get('general', ''))
                        if desc:
                            st.markdown(desc)
                        else:
                             st.markdown(f"**Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")
                    else:
                        st.markdown(f"**Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")

                    st.write("---")

            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã nhập.")
        else:
            st.info("Nhập vào kích thước lốp ở trên để bắt đầu tra cứu.")

    # --- Công cụ 2: Tính chi phí ---
    with tab_cost:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        
        col1_cost, col2_cost = st.columns(2)
        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, 
                                     help="Thông thường, lốp xe đi được từ 40,000 km đến 70,000 km.")
        with col2_cost:
            if gia_lop > 0 and tuoi_tho > 0:
                chi_phi_per_km = gia_lop / tuoi_tho
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", 
                          value=f"{chi_phi_per_km:,.2f} VNĐ / km",
                          help="Chi phí này chỉ mang tính tham khảo.")
            else:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí.")
