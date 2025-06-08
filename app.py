import streamlit as st
import pandas as pd
import re

# --- PHẦN 1: CẤU HÌNH TRANG WEB ---
# Lệnh này phải được gọi đầu tiên để thiết lập tiêu đề và layout cho trang
st.set_page_config(page_title="Công Cụ Tư Vấn Lốp Xe", layout="wide")

# --- PHẦN 2: TẢI VÀ XỬ LÝ DỮ LIỆU ---
@st.cache_data # Decorator giúp lưu kết quả xử lý dữ liệu, tăng tốc độ cho những lần chạy sau
def load_all_data():
    """
    Hàm này có nhiệm vụ tải, xử lý và kết hợp tất cả các file dữ liệu.
    Nó sẽ trả về hai DataFrame: một là dữ liệu lốp tổng hợp, hai là dữ liệu xe.
    """
    try:
        # Đọc tất cả file CSV với kiểu dữ liệu là 'str' (văn bản) để tránh lỗi
        df_prices_raw = pd.read_csv('BẢNG GIÁ BÁN LẺ_19_05_2025.csv', dtype=str)
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG - Mã Gai.csv', dtype=str)
        df_xe1_raw = pd.read_csv('Tyre1.csv', dtype=str)
        df_xe2_raw = pd.read_csv('tyre_bosung.csv', dtype=str)

        # 1. XỬ LÝ BẢNG GIÁ (df_prices)
        price_cols = ['stt', 'quy_cach', 'ma_gai', 'xuat_xu', 'gia_ban_le']
        num_price_cols = min(len(df_prices_raw.columns), len(price_cols))
        df_prices = df_prices_raw.iloc[:, :num_price_cols]
        df_prices.columns = price_cols[:num_price_cols]
        
        if 'gia_ban_le' in df_prices.columns:
            df_prices['gia_ban_le'] = pd.to_numeric(
                df_prices['gia_ban_le'].str.replace(r'[^\d]', '', regex=True), 
                errors='coerce'
            )
            df_prices.dropna(subset=['gia_ban_le'], inplace=True)

        # 2. XỬ LÝ MÔ TẢ MÃ GAI (df_magai)
        magai_cols = ['ma_gai', 'mo_ta_gai', 'nhu_cau']
        num_magai_cols = min(len(df_magai_raw.columns), len(magai_cols))
        df_magai = df_magai_raw.iloc[:, :num_magai_cols]
        df_magai.columns = magai_cols[:num_magai_cols]
        
        # 3. XỬ LÝ DỮ LIỆU XE (df_xe1, df_xe2)
        xe_cols = ['hang_xe', 'mau_xe', 'doi_xe', 'quy_cach']
        
        num_xe1_cols = min(len(df_xe1_raw.columns), len(xe_cols))
        df_xe1 = df_xe1_raw.iloc[:, :num_xe1_cols]
        df_xe1.columns = xe_cols[:num_xe1_cols]

        num_xe2_cols = min(len(df_xe2_raw.columns), len(xe_cols))
        df_xe2 = df_xe2_raw.iloc[:, :num_xe2_cols]
        df_xe2.columns = xe_cols[:num_xe2_cols]

        df_xe = pd.concat([df_xe1, df_xe2], ignore_index=True)
        df_xe.dropna(subset=['hang_xe', 'mau_xe', 'quy_cach'], inplace=True)
        
        # Tạo cột 'display_name' để hiển thị đẹp hơn
        df_xe['display_name'] = df_xe['hang_xe'] + " " + df_xe['mau_xe']

        # 4. KẾT HỢP CÁC BẢNG DỮ LIỆU
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền các giá trị còn trống
        if 'nhu_cau' not in df_master.columns: df_master['nhu_cau'] = 'Tiêu chuẩn'
        df_master['nhu_cau'] = df_master['nhu_cau'].fillna('Tiêu chuẩn')
        
        if 'mo_ta_gai' not in df_master.columns: df_master['mo_ta_gai'] = 'Gai lốp tiêu chuẩn.'
        df_master['mo_ta_gai'] = df_master['mo_ta_gai'].fillna('Gai lốp tiêu chuẩn của Linglong.')

        # Làm sạch khoảng trắng thừa
        for col in ['quy_cach', 'ma_gai', 'xuat_xu', 'nhu_cau']:
             if col in df_master.columns:
                df_master[col] = df_master[col].str.strip()
        
        for col in ['hang_xe', 'mau_xe', 'quy_cach']:
             if col in df_xe.columns:
                df_xe[col] = df_xe[col].str.strip()

        return df_master, df_xe

    except FileNotFoundError as e:
        st.error(f"Lỗi không tìm thấy file: **{e.filename}**. Vui lòng kiểm tra lại tên file.")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi đọc file: {e}")
        return pd.DataFrame(), pd.DataFrame()


# --- PHẦN 3: KHỞI TẠO VÀ CHẠY ỨNG DỤNG ---
df_master, df_xe = load_all_data()

# --- Giao diện chính ---
st.title("️🚗 BỘ CÔNG CỤ TƯ VẤN LỐP XE LINGLONG")
st.markdown("Xây dựng bởi **Chuyên Gia Lốp Thầm Lặng** - Dành cho những lựa chọn sáng suốt.")

if df_master.empty or df_xe.empty:
    st.warning("Không thể khởi động ứng dụng do lỗi tải dữ liệu. Vui lòng kiểm tra lại thông báo lỗi ở trên.")
else:
    # THAY ĐỔI: Thêm Tab "Tra Cứu Theo Size" và đổi tên các Tab cũ
    tab1, tab2, tab3 = st.tabs([
        "**⚙️ Tư Vấn Theo Xe**", 
        "**🔍 Tra Cứu Theo Size**", 
        "**🧮 Tính Chi Phí Lốp**"
    ])

    # --- Công cụ 1: Tư vấn theo xe ---
    with tab1:
        st.header("Tìm lốp Linglong phù hợp với xe của bạn")
        
        col1, col2 = st.columns(2)
        with col1:
            hang_xe_list = sorted(df_xe['hang_xe'].unique())
            selected_hang_xe = st.selectbox("1. Chọn Hãng Xe:", hang_xe_list)
        with col2:
            mau_xe_list = sorted(df_xe[df_xe['hang_xe'] == selected_hang_xe]['mau_xe'].unique())
            selected_mau_xe = st.selectbox("2. Chọn Mẫu Xe:", mau_xe_list)

        lop_theo_xe_series = df_xe[(df_xe['hang_xe'] == selected_hang_xe) & (df_xe['mau_xe'] == selected_mau_xe)]['quy_cach']
        
        if not lop_theo_xe_series.empty:
            lop_theo_xe = lop_theo_xe_series.iloc[0]
            
            col_kich_thuoc, col_nhu_cau = st.columns(2)
            with col_kich_thuoc:
                 st.text_input("3. Kích thước lốp theo xe:", value=lop_theo_xe, disabled=True, key="lop_theo_xe_display")
            
            # SỬA LỖI LOGIC: Thêm tùy chọn "Tất cả" cho nhu cầu
            nhu_cau_list = ['Tất cả'] + sorted(df_master[df_master['quy_cach'].str.contains(lop_theo_xe, case=False, na=False)]['nhu_cau'].unique())
            
            with col_nhu_cau:
                selected_nhu_cau = st.selectbox("4. Chọn nhu cầu chính của bạn:", nhu_cau_list, help="Êm ái, Tiết kiệm, Thể thao hay Đa dụng?")

            if st.button("🔍 Tìm Lốp Ngay", type="primary", use_container_width=True):
                # SỬA LỖI LOGIC: Dùng .str.contains thay vì == để tìm kiếm linh hoạt hơn
                results = df_master[df_master['quy_cach'].str.contains(lop_theo_xe, case=False, na=False)]
                
                # Lọc thêm theo nhu cầu nếu người dùng không chọn "Tất cả"
                if selected_nhu_cau != 'Tất cả':
                    results = results[results['nhu_cau'] == selected_nhu_cau]

                st.success(f"Đã tìm thấy **{len(results)}** loại lốp phù hợp cho xe **{selected_hang_xe} {selected_mau_xe}**.")
                if not results.empty:
                    for index, row in results.iterrows():
                        with st.expander(f"**Mã gai: {row['ma_gai']}** - Giá: {row['gia_ban_le']:,} VNĐ", expanded=True):
                            st.markdown(f"**- Mô tả:** {row['mo_ta_gai']}\n\n**- Nhu cầu:** {row['nhu_cau']}\n\n**- Xuất xứ:** {row['xuat_xu'].title()}")
                else:
                    st.warning("Rất tiếc, không tìm thấy lốp Linglong nào khớp chính xác với lựa chọn này.")
        else:
            st.error(f"Không tìm thấy dữ liệu lốp cho xe {selected_hang_xe} {selected_mau_xe}.")

    # --- Công cụ 2: Tra cứu giá theo size (TÍNH NĂNG MỚI) ---
    with tab2:
        st.header("Tra cứu giá lốp Linglong theo kích thước")
        
        size_query = st.text_input(
            "Nhập kích thước lốp bạn muốn tìm:", 
            placeholder="Ví dụ: 215/55R17 hoặc 185R14C"
        )

        if size_query: # Tự động tìm kiếm khi người dùng nhập
            search_term = size_query.strip()
            # SỬA LỖI KEYERROR: Thay "gia ban le" bằng "gia_ban_le"
            results = df_master[df_master['quy_cach'].str.contains(search_term, case=False, na=False)].sort_values(by="gia_ban_le")
            
            st.write("---")
            st.subheader(f"Kết quả tìm kiếm cho \"{search_term}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                # Hiển thị kết quả trong các thẻ đẹp mắt
                for index, row in results.iterrows():
                    with st.container():
                        st.markdown(f"#### {row['quy_cach']}")
                        st.markdown(f"**Mã gai:** {row['ma_gai']} | **Giá bán lẻ:** <span style='color: #28a745; font-weight: bold;'>{row['gia_ban_le']:,} VNĐ</span>", unsafe_allow_html=True)
                        st.markdown(f"**Nhu cầu:** {row['nhu_cau']}")
                        st.markdown(f"**Mô tả:** {row['mo_ta_gai']}")
                        st.markdown("---")
            else:
                st.warning("Không tìm thấy sản phẩm nào phù hợp với kích thước bạn đã nhập.")
        else:
            st.info("Nhập vào kích thước lốp ở trên để bắt đầu tra cứu.")

    # --- Công cụ 3: Tính chi phí ---
    with tab3:
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
