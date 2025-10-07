dax = """
// DAX Query — standardized (no Grand Total, no TOPN, no FormatString)
DEFINE
    VAR __DS0FilterTable =
        TREATAS(
            { "Tháng trước", "Hiện tại", "Chênh lệch (%)" },
            'So sánh tháng trước'[So sánh]
        )

    VAR __DS0FilterTable2 =
        TREATAS( { "Thủy Hải Sản Các Loại" }, 'd_sanpham'[nganh_hang] )

    VAR __DS0FilterTable3 =
        FILTER(
            KEEPFILTERS( VALUES('d_ngay'[ngay]) ),
            'd_ngay'[ngay] >= DATE(2025,10,1) && 'd_ngay'[ngay] < DATE(2025,10,7)
        )

    VAR __DS0FilterTable4 =
        FILTER(
            KEEPFILTERS( VALUES('d_sieuthi'[ma_sieu_thi]) ),
            NOT( ISBLANK('d_sieuthi'[ma_sieu_thi]) )
        )

    VAR __DS0FilterTable5 =
        FILTER(
            KEEPFILTERS( VALUES('d_sanpham'[ten_san_pham]) ),
            NOT( 'd_sanpham'[ten_san_pham] IN { BLANK() } )
        )

    VAR __DS0Core =
        SUMMARIZECOLUMNS(
            'd_sieuthi'[rsm],
            __DS0FilterTable,
            __DS0FilterTable2,
            __DS0FilterTable3,
            __DS0FilterTable4,
            __DS0FilterTable5,
            "SL_nhập_xét_theo_tổng__KG_", 'measure nhập'[SL nhập xét theo tổng (KG)],
            "SL_bán__KG_", 'measure xuất'[SL bán (KG)],
            "Tỉ_lệ_Bán_Nhập", 'measure tỉ lệ'[Tỉ lệ Bán/Nhập]
        )

EVALUATE
    __DS0Core

ORDER BY
    'd_sieuthi'[rsm] DESC

"""