import streamlit as st
import pandas as pd
import re

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
        # SỬA ĐỔI: Sử dụng file "Mã Gai LINGLONG.csv" mới
        df_magai_raw = pd.read_csv('Mã Gai LINGLONG.csv', dtype=str)

        # 1. XỬ LÝ BẢNG GIÁ (df_prices)
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

        # 2. XỬ LÝ MÔ TẢ MÃ GAI (df_magai)
        # THÊM TÍNH NĂNG: Thêm các cột mới theo yêu cầu
        magai_cols = ['ma_gai', 'nhu_cau', 'ung_dung_cu_the', 'uu_diem_cot_loi', 'link_hinh_anh']
        num_magai_cols = min(len(df_magai_raw.columns), len(magai_cols))
        df_magai = df_magai_raw.iloc[:, :num_magai_cols]
        df_magai.columns = magai_cols[:num_magai_cols]
        
        # 3. KẾT HỢP CÁC BẢNG DỮ LIỆU
        df_master = pd.merge(df_prices, df_magai, on='ma_gai', how='left')

        # Điền các giá trị còn trống để đảm bảo không bị lỗi
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
        return pd.DataFrame() # Trả về DataFrame rỗng nếu có lỗi
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
        
        size_query = st.text_input(
            "Nhập kích thước lốp bạn muốn tìm:", 
            placeholder="Ví dụ: 215/55R17 hoặc 185R14C"
        )

        if size_query: # Tự động tìm kiếm khi người dùng nhập
            search_term = size_query.strip()
            # Tìm kiếm gần đúng và sắp xếp theo giá
            results = df_master[df_master['quy_cach'].str.contains(search_term, case=False, na=False)]
            
            # Chỉ sắp xếp theo giá nếu cột 'gia_ban_le' tồn tại
            if 'gia_ban_le' in results.columns:
                results = results.sort_values(by="gia_ban_le")

            st.write("---")
            st.subheader(f"Kết quả tìm kiếm cho \"{search_term}\"")
            
            if not results.empty:
                st.success(f"Đã tìm thấy **{len(results)}** sản phẩm phù hợp.")
                
                # THAY ĐỔI: Hiển thị kết quả dạng bảng
                for index, row in results.iterrows():
                    st.markdown(f"#### {row['quy_cach']} / {row['ma_gai']}")
                    
                    price_str = f"{row['gia_ban_le']:,} VNĐ" if pd.notna(row['gia_ban_le']) else "Chưa có giá"
                    link_str = f"<a href='{row['link_hinh_anh']}' target='_blank'>Xem Hình Ảnh/Video</a>" if row['link_hinh_anh'] not in ['Chưa có thông tin', ''] else "Không có"

                    # SỬA LỖI: Thay thế to_markdown bằng cách hiển thị trực tiếp với st.columns để tránh lỗi ImportError
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown("**Giá Bán Lẻ**")
                        st.markdown("**Ứng dụng cụ thể**")
                        st.markdown("**Ưu điểm cốt lõi**")
                        st.markdown("**Phân loại**")
                        st.markdown("**Media**")
                    with col2:
                        st.markdown(f"**{price_str}**")
                        st.markdown(row['ung_dung_cu_the'])
                        st.markdown(row['uu_diem_cot_loi'])
                        st.markdown(row['nhu_cau'])
                        st.markdown(link_str, unsafe_allow_html=True)
                    
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
