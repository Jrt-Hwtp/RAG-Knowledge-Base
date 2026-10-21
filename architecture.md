# System Architecture Overview (ภาพรวมสถาปัตยกรรมระบบ)

เอกสารนี้อธิบายโครงสร้างระบบเบื้องต้นของโปรเจกต์ Development

## 1. Frontend (ส่วนหน้าบ้าน)
- **Framework:** React.js
- **Hosting:** AWS S3 + CloudFront
- **State Management:** Redux

## 2. Backend (ส่วนหลังบ้าน)
- **Framework:** Node.js (Express)
- **Database:** PostgreSQL สำหรับเก็บข้อมูลผู้ใช้งานและธุรกรรม
- **Cache:** Redis สำหรับช่วยลดภาระโหลดของ Database

## 3. Authentication System (ระบบยืนยันตัวตน)
ระบบ Authentication ของเรามีการเชื่อมต่อกับ **Google OAuth 2.0 API** เพื่อให้ผู้ใช้งานสามารถเข้าสู่ระบบ (Login) ด้วยบัญชี Google ได้อย่างรวดเร็ว โดยหลังจากยืนยันตัวตนสำเร็จ ระบบหลังบ้านจะสร้าง JWT (JSON Web Token) เพื่อใช้จัดการสิทธิ์ (Session) ต่อไป
- **ไฟล์หลักที่จัดการระบบนี้:** `auth.js`
- **Third-party ที่เชื่อมต่อ:** Google OAuth

## 4. Integration
- **CI/CD:** GitHub Actions สำหรับทำ Automated Test และ Deploy
- **Issue Tracking:** ใช้ Jira สำหรับติดตามบั๊ก (Bug) และงาน (Task)