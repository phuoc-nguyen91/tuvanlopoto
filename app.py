import streamlit as st
import pandas as pd
import re
import google.generativeai as genai

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Công Cụ Tra Cứu Lốp Xe", layout="wide")

# --- PHẦN 1.5: CẤU HÌNH API AN TOÀN VỚI STREAMLIT SECRETS ---
api_configured = False
try:
    # Cố gắng lấy API key từ trình quản lý bí mật của Streamlit
    if 'google_api_key' in st.secrets:
        genai.configure(api_key=st.secrets["google_api_key"])
        api_configured = True
except Exception as e:
    # Không hiển thị lỗi cho người dùng cuối để tăng tính bảo mật
    print(f"Lỗi cấu hình API: {e}")


# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data
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
        df_prices = df_prices_raw.iloc[:, :len(price_cols)]
        df_prices.columns = price_cols
        
        if 'gia_ban_le' in df_prices.columns:
            df_prices['gia_ban_le'] = pd.to_numeric(
                df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), 
                errors='coerce'
            )
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)

        # 2. XỬ LÝ MÔ TẢ MÃ GAI
        magai_cols = ['ma_gai', 'nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']
        df_magai = df_magai_raw.iloc[:, :len(magai_cols)]
        df_magai.columns = magai_cols
        
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
        
        # Tạo cột 'base_size' để gom nhóm các size lốp
        df_master['base_size'] = df_master['quy_cach'].str.extract(r'(\d+/\d+R\d+)')

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
        
        # Lấy danh sách từ cột 'base_size' đã được làm sạch
        unique_sizes = sorted(df_master['base_size'].dropna().unique())
        options = ["--- Chọn hoặc tìm size lốp ---"] + unique_sizes
        
        size_query = st.selectbox(
            "Chọn kích thước lốp bạn muốn tìm:", 
            options=options,
            help="Bạn có thể gõ để tìm kiếm size trong danh sách."
        )

        # Chỉ thực hiện tìm kiếm khi người dùng đã chọn một size cụ thể
        if size_query != "--- Chọn hoặc tìm size lốp ---":
            search_term = size_query
            # Tìm kiếm dựa trên cột 'base_size' để lấy tất cả các biến thể
            results = df_master[df_master['base_size'] == search_term].copy()
            
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
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

                    # THAY ĐỔI: Sử dụng AI để tạo nội dung cho phần "Ưu điểm cốt lõi"
                    if api_configured:
                        try:
                            # Tối ưu prompt để AI trả lời đúng trọng tâm
                            prompt = (
                                f"Với vai trò là một chuyên gia tư vấn lốp xe, hãy viết một đoạn ngắn (2-3 câu) nêu bật các ưu điểm cốt lõi của lốp Linglong có thông số {row['quy_cach']} và mã gai {row['ma_gai']}. "
                                f"Sau đó, liệt kê dưới dạng gạch đầu dòng một vài dòng xe phổ biến tại Việt Nam thường sử dụng loại lốp này."
                                f"Sử dụng thông tin gợi ý sau nếu có: {row['uu_diem_cot_loi']}."
                            )
                            model = genai.GenerativeModel('gemini-1.5-pro-latest')
                            with st.spinner("AI đang phân tích sản phẩm..."):
                                response = model.generate_content(prompt)
                                st.markdown(response.text)
                        except Exception as e:
                            # Nếu AI lỗi, hiển thị thông tin có sẵn
                            st.markdown(f"**👍 Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")
                            st.warning(f"Không thể tải gợi ý từ AI: {e}")
                    else:
                        # Hiển thị thông tin mặc định nếu không có API key
                        st.markdown(f"**👍 Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")

                    # Báo giá khuyến mãi
                    if pd.notna(row['gia_ban_le']):
                        with st.container():
                            st.markdown("🎁 **Báo giá khuyến mãi:**")
                            price_for_2 = (row['gia_ban_le'] * 2) * 0.95
                            price_for_4 = (row['gia_ban_le'] * 4) * 0.90
                            promo_col1, promo_col2 = st.columns(2)
                            with promo_col1:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;• Mua 2 lốp (giảm 5%): **<span style='color: #ff4b4b;'>{price_for_2:,.0f} VNĐ</span>**", unsafe_allow_html=True)
                            with promo_col2:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;• Mua 4 lốp (giảm 10%): **<span style='color: #ff4b4b;'>{price_for_4:,.0f} VNĐ</span>**", unsafe_allow_html=True)
                    
                    st.markdown("---")

                # Di chuyển CTA ra ngoài vòng lặp
                st.markdown("##### **Để được tư vấn và báo giá tốt nhất, vui lòng liên hệ:**")
                
                col_cta_1, col_cta_2 = st.columns([2,1])
                with col_cta_1:
                    st.markdown("📞 **HOTLINE:** **0943 24 24 24**")
                    st.markdown("💬 **Zalo:** [https://zalo.me/0943242424](https://zalo.me/0943242424)")
                    st.markdown("📍 **Địa chỉ:** 114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM")
                with col_cta_2:
                    try:
                        st.image("qr.jpg", width=150, caption="Quét mã để kết bạn Zalo")
                    except Exception as e:
                        st.info("Không tìm thấy file qr.jpg")

                st.markdown("<hr style='border: 2px solid #ff4b4b; border-radius: 5px;'/>", unsafe_allow_html=True)


            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã nhập.")
        else:
            st.info("Vui lòng chọn một kích thước lốp từ danh sách ở trên để bắt đầu tra cứu.")

    # --- Công cụ 2: Tính chi phí ---
    with tab_cost:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        
        col1_cost, col_cost = st.columns(2)
        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, 
                                     help="Thông thường, lốp xe đi được từ 40,000 km đến 70,000 km.")
        with col_cost:
            if gia_lop > 0 and tuoi_tho > 0:
                chi_phi_per_km = gia_lop / tuoi_tho
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", 
                          value=f"{chi_phi_per_km:,.2f} VNĐ / km",
                          help="Chi phí này chỉ mang tính tham khảo.")
            else:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí.")
