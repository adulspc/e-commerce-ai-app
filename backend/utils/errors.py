"""Domain errors returned to the browser as short Thai messages."""


class AppError(Exception):
    status_code = 400
    code = "app_error"
    default_message = "คำขอไม่สำเร็จ"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class SessionNotFoundError(AppError):
    status_code = 404
    code = "session_not_found"
    default_message = "ไม่พบชุดข้อมูลนี้ ลองอัปโหลดไฟล์อีกครั้ง"


class InvalidSessionStateError(AppError):
    status_code = 409
    code = "invalid_session_state"
    default_message = "ยังไม่ถึงขั้นตอนนี้ ทำขั้นตอนก่อนหน้าให้ครบก่อน"

    def __init__(self, actual: str) -> None:
        labels = {
            "uploaded": "อัปโหลดแล้ว",
            "processed": "ประมวลผลแล้ว",
            "clustered": "จัดกลุ่มแล้ว",
        }
        actual_label = labels.get(actual, actual)
        super().__init__(f"สถานะปัจจุบันคือ {actual_label} จึงยังทำขั้นตอนนี้ไม่ได้")


class InvalidCsvError(AppError):
    status_code = 400
    code = "invalid_csv"
    default_message = "อ่านไฟล์ CSV ไม่ได้ ตรวจสอบว่าเป็นไฟล์ .csv และไม่ได้เสียหาย"


class MissingColumnsError(AppError):
    status_code = 400
    code = "missing_columns"
    default_message = "ไม่พบคอลัมน์ราคาหรือจำนวนขาย เลือกคอลัมน์ให้ครบแล้วลองอีกครั้ง"

    def __init__(self, columns: list[str] | None = None, message: str | None = None) -> None:
        if message:
            super().__init__(message)
            return
        if columns:
            joined = ", ".join(columns)
            super().__init__(f"ไม่พบคอลัมน์ที่ต้องใช้: {joined}")
            return
        super().__init__()


class EmptyDatasetError(AppError):
    status_code = 400
    code = "empty_dataset"
    default_message = "ไฟล์ไม่มีข้อมูลสินค้า"


class NonNumericValueError(AppError):
    status_code = 400
    code = "non_numeric_values"
    default_message = "พบค่าที่ไม่ใช่ตัวเลขในคอลัมน์ราคา ส่วนลด หรือจำนวนขาย"


class InvalidKError(AppError):
    status_code = 400
    code = "invalid_k"
    default_message = "จำนวนกลุ่มต้องอยู่ระหว่าง 2 ถึง 10"


class DatasetTooSmallError(AppError):
    status_code = 400
    code = "dataset_too_small"
    default_message = "ข้อมูลหลังทำความสะอาดมีน้อยกว่า 10 รายการ จึงยังจัดกลุ่มไม่ได้"


class KTooLargeError(AppError):
    status_code = 400
    code = "k_too_large"
    default_message = "จำนวนกลุ่มต้องน้อยกว่าจำนวนสินค้าที่ใช้วิเคราะห์"


class MachineLearningError(AppError):
    status_code = 500
    code = "machine_learning_error"
    default_message = "จัดกลุ่มสินค้าไม่สำเร็จ ลองเลือกจำนวนกลุ่มใหม่หรือตรวจสอบข้อมูล"


class ClusterNotFoundError(AppError):
    status_code = 404
    code = "cluster_not_found"
    default_message = "ไม่พบกลุ่มนี้ในผลการจัดกลุ่มล่าสุด"


class ProductNotFoundError(AppError):
    status_code = 404
    code = "product_not_found"
    default_message = "ไม่พบสินค้านี้ในชุดข้อมูลที่จัดกลุ่มแล้ว"
