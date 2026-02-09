# Attendance Monitoring System using CNN and RFID

A robust, intelligent web application built with Python and Django. This system is designed to automate student attendance using Biometric Face Recognition (CNN) and RFID hardware, handling complex scheduling conflicts, redundancy checks, and role-based access control.

## 📋 Features (Meeting Requirements)

### Core Functionality
* **Dual Authentication:** Uses **Convolutional Neural Networks (CNN)** with `FaceNet` and `TensorFlow` for facial recognition, plus an **RFID** hardware fallback for reliability.
* **Role-Based Access:** Distinct portals for **Admins** (Configuration), **Teachers** (Attendance Execution), and **Students** (Monitoring).
* **Real-time Processing:** Utilizes `OpenCV` and `Threading` to handle live video feeds for face detection without blocking the web interface.
* **Data Integrity:** Securely maps recognized faces to Student IDs using a trained classifier model.

### 🌟 Bonus Features Implemented
1.  **Conflict Detection:** The scheduler implements a validation algorithm that checks Time, Date, and Room availability. If a new class overlaps with an existing one, the system blocks the creation to prevent double-booking.
2.  **Anti-Redundancy Logic:** The system tracks the "Checked-In" state of every student per session. If a student scans their face or taps their RFID card a second time, the system rejects the duplicate entry and notifies that they are "Already Checked In."
3.  **Automated Notifications:** Integrated `django.core.mail` to send system alerts or attendance reports.
4.  **Face Preprocessing:** Includes a dedicated `preprocess` module to align and crop faces before training, improving recognition accuracy.

## 🛠️ Installation

1.  **Prerequisites:**
    * Python 3.x installed.
    * Webcam (for Face Recognition).
    * RFID Reader (RC522 connected to Microcontroller/GPIO).

2.  **Install Dependencies:**
    ```bash
    pip install django opencv-python tensorflow pillow numpy
    # Note: Requires tensorflow.compat.v1 support
    ```

## 📝 Limitations & Assumptions
1.  **Hardware Dependency:** The system assumes a camera and RFID reader are connected to the host machine or accessible via network stream.
2.  **Lighting Conditions:** Face recognition accuracy relies on adequate lighting during the "Start Attendance" session.

## 🚀 How to Run

1.  Clone this repository.
2.  **Database Setup:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
3.  **Train the Model:**
    * Ensure student photos are in the `dataset` folder.
    * Run the training script (e.g., `python training.py`) to generate the classifier.
4.  **Run the Server:**
    ```bash
    python manage.py runserver
    ```
5.  **Teacher Action:**
    * Log in as a Teacher.
    * Navigate to "My Subjects" and click **"Start Attendance"**.
    * The system will open the camera feed/RFID listener.

## 📂 System Roles

The system is architected around three specific user levels:

```json
{
    "User_Roles": [
        {
            "Role": "Admin",
            "Access": "Full CRUD on Users, Conflict-Free Scheduling, Classroom Management"
        },
        {
            "Role": "Teacher",
            "Access": "Start Attendance (CNN/RFID), Manual Override, View Class History"
        },
        {
            "Role": "Student",
            "Access": "View Enrolled Subjects, Check Attendance Status"
        }
    ]
}
