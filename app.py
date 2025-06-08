import streamlit as st
import pandas as pd
import re
import google.generativeai as genai

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Công Cụ Tra Cứu Lốp Xe", layout="wide")

# --- PHẦN 1.5: CẤU HÌNH API AN TOÀN VỚI STREAMLIT SECRETS ---
api_configured = False
try:
    if 'google_api_key' in st.secrets:
        genai.configure(api_key=st.secrets["google_api_key"])
        api_configured = True
except Exception as e:
    print(f"Lỗi cấu hình API: {e}")


# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data
def load_all_data():
    """
    Hàm này có nhiệm vụ tải và xử lý dữ liệu từ các file CSV.
    """
    try:
        # Đọc tất cả các file CSV cần thiết
        df_prices_raw = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG.csv', dtype=str)
        df_xe1_raw = pd.read_csv('Tyre1.csv', dtype=str)
        df_xe2_raw = pd.read_csv('tyre_bosung.csv', dtype=str)

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
        
        # 3. XỬ LÝ DỮ LIỆU XE
        xe_cols = ['hang_xe', 'mau_xe', 'doi_xe', 'quy_cach']
        df_xe1 = df_xe1_raw.iloc[:, :len(xe_cols)]
        df_xe1.columns = xe_cols
        df_xe2 = df_xe2_raw.iloc[:, :len(xe_cols)]
        df_xe2.columns = xe_cols
        df_xe = pd.concat([df_xe1, df_xe2], ignore_index=True)
        df_xe.dropna(subset=['hang_xe', 'mau_xe', 'quy_cach'], inplace=True)
        
        # 4. KẾT HỢP DỮ LIỆU LỐP
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền và làm sạch dữ liệu
        for col in ['nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']:
            if col not in df_master.columns:
                df_master[col] = 'Chưa có thông tin'
            df_master[col] = df_master[col].fillna('Chưa có thông tin')

        for df in [df_master, df_xe]:
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip()
        
        return df_master, df_xe

    except FileNotFoundError as e:
        st.error(f"Lỗi không tìm thấy file: **{e.filename}**. Vui lòng kiểm tra lại.")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc file: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- PHẦN 3: KHỞI TẠO VÀ CHẠY ỨNG DỤNG ---
df_master, df_xe = load_all_data()

# --- Giao diện chính ---
st.title("️🚗 BỘ CÔNG CỤ TRA CỨU LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

if df_master.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại thông báo lỗi ở trên.")
else:
    tab_search, tab_cost = st.tabs(["**🔍 Tra Cứu Lốp Theo Size**", "**🧮 Tính Chi Phí Lốp**"])

    with tab_search:
        st.header("Tra cứu lốp Linglong theo kích thước")
        
        unique_sizes = sorted(df_master['quy_cach'].unique())
        options = ["--- Chọn hoặc tìm size lốp ---"] + unique_sizes
        size_query = st.selectbox(
            "Chọn kích thước lốp bạn muốn tìm:", 
            options=options,
            help="Bạn có thể gõ để tìm kiếm size trong danh sách."
        )

        if size_query != "--- Chọn hoặc tìm size lốp ---":
            results = df_master[df_master['quy_cach'] == size_query]
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
            st.subheader(f"Kết quả tra cứu cho \"{size_query}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                
                # --- Hiển thị thông tin từ file CSV trước ---
                for index, row in results.iterrows():
                    price_str = f"{row['gia_ban_le']:,} VNĐ" if pd.notna(row['gia_ban_le']) else "Chưa có giá"
                    col_title, col_price = st.columns([3, 1])
                    with col_title:
                        st.markdown(f"#### {row['quy_cach']} / {row['ma_gai']}")
                    with col_price:
                        st.markdown(f"<div style='text-align: right; font-size: 1.2em; color: #28a745; font-weight: bold;'>{price_str}</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"**👍 Ưu điểm cốt lõi:** {row['uu_diem_cot_loi']}")
                    
                    # Hiển thị bảng giá khuyến mãi
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

                # --- Hiển thị thông tin từ AI và Web Search sau ---
                with st.expander("🚙 **Các dòng xe tương thích (Nhấn để xem)**", expanded=True):
                    # Hiển thị thông tin xe từ file CSV có sẵn
                    matching_cars_df = df_xe[df_xe['quy_cach'] == size_query]
                    if not matching_cars_df.empty:
                        st.markdown("**Các dòng xe trong dữ liệu có sẵn:**")
                        st.dataframe(matching_cars_df[['hang_xe', 'mau_xe', 'doi_xe']].rename(columns={'hang_xe': 'Hãng Xe', 'mau_xe': 'Mẫu Xe', 'doi_xe': 'Đời Xe'}), use_container_width=True)
                    else:
                        st.info("Không tìm thấy dữ liệu xe tương thích trong hệ thống có sẵn.")

                    # Gọi AI để tìm thêm thông tin
                    if api_configured:
                        st.markdown("**Gợi ý thêm từ AI (dựa trên dữ liệu web):**")
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash-latest')
                            prompt = f"Liệt kê các dòng xe phổ biến tại Việt Nam sử dụng lốp size {size_query}. Trình bày dưới dạng một danh sách gạch đầu dòng đơn giản."
                            with st.spinner("AI đang tìm kiếm thêm các dòng xe khác..."):
                                response = model.generate_content(prompt)
                                st.markdown(response.text)
                        except Exception as e:
                            st.warning(f"Không thể tìm kiếm thêm bằng AI: {e}")

                # Hiển thị CTA ở cuối
                st.markdown("---")
                st.markdown("##### **Để được tư vấn và báo giá tốt nhất, vui lòng liên hệ:**")
                col_cta_1, col_cta_2 = st.columns([2,1])
                with col_cta_1:
                    st.markdown("📞 **HOTLINE:** **0943 24 24 24**")
                    st.markdown("💬 **Zalo:** [https://zalo.me/0943242424](https://zalo.me/0943242424)")
                    st.markdown("📍 **Địa chỉ:** 114 Đường Số 2, Trường Thọ, Thủ Đức, TPHCM")
                with col_cta_2:
                    try:
                        st.image("qr.jpg", width=150, caption="Quét mã để kết bạn Zalo")
                    except:
                        st.info("Không tìm thấy file qr.jpg")
                st.markdown("<hr style='border: 2px solid #ff4b4b; border-radius: 5px;'/>", unsafe_allow_html=True)

            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã chọn.")
        else:
            st.info("Vui lòng chọn một kích thước lốp từ danh sách ở trên để bắt đầu tra cứu.")

    with tab_cost:
        st.header("Ước tính chi phí sử dụng lốp trên mỗi Kilômét")
        col1_cost, col2_cost = st.columns(2)
        with col1_cost:
            gia_lop = st.number_input("Nhập giá 1 lốp xe (VNĐ):", min_value=0, step=100000)
            tuoi_tho = st.number_input("Tuổi thọ dự kiến của lốp (km):", min_value=10000, step=5000, value=45000, help="Thông thường, lốp xe đi được từ 40,000 km đến 70,000 km.")
        with col2_cost:
            if gia_lop > 0 and tuoi_tho > 0:
                chi_phi_per_km = gia_lop / tuoi_tho
                st.metric(label="CHI PHÍ ƯỚC TÍNH MỖI KM", value=f"{chi_phi_per_km:,.2f} VNĐ / km", help="Chi phí này chỉ mang tính tham khảo.")
            else:
                st.info("Nhập giá và tuổi thọ dự kiến để xem chi phí.")
