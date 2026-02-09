# Classroom Scheduling System

A modern and efficient classroom scheduling system built with Django, featuring a beautiful UI and comprehensive management tools for teachers, students, subjects, and schedules.

## Features

- **User Authentication & Authorization**
  - Secure login/logout system
  - Role-based access control (Superuser/User)
  - Password management
  - Session security

- **Information Management**
  - Teacher management
  - Student management
  - Classroom management
  - Subject management
  - Schedule management

- **Modern UI/UX**
  - Responsive dashboard
  - Mobile-friendly design
  - Real-time statistics
  - Interactive navigation
  - Beautiful forms and lists

## Prerequisites

- Python 3.8 or higher
- MySQL (via XAMPP)
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd itelec2
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure MySQL database:
   - Start XAMPP and ensure MySQL is running
   - Create a new database named 'scheduling'

6. Apply migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

8. Run the development server:
   ```bash
   python manage.py runserver
   ```

9. Access the application:
   - Open your browser and navigate to `http://localhost:8000`
   - Login with your superuser credentials

## Usage

1. **Dashboard**
   - View quick statistics
   - Access today's schedule
   - Quick navigation to all features

2. **User Management**
   - Create and manage user accounts
   - Assign roles (Superuser/User)
   - Change passwords

3. **Schedule Management**
   - Create and edit class schedules
   - View schedules by room, teacher, or student
   - Automatic conflict detection

4. **Information Management**
   - Add/Edit/Delete teachers
   - Manage student records
   - Configure classrooms
   - Set up subjects

## Security Features

- CSRF protection
- Secure password hashing
- Session management
- Form validation
- Protected routes

## Tech Stack

- **Backend**: Django 4.2.7
- **Database**: MySQL
- **Frontend**: Bootstrap 5.2.3
- **Icons**: Font Awesome 6.0
- **Additional Libraries**:
  - django-crispy-forms
  - crispy-bootstrap5
  - Pillow
  - python-dotenv

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please contact the development team or raise an issue in the repository.
