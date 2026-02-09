// Function to show a success notification
function showSuccess(message) {
    Swal.fire({
        title: 'Success',
        text: message,
        icon: 'success',
        toast: true,
        position: 'center',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show an error notification
function showError(message) {
    Swal.fire({
        title: 'Error',
        text: message,
        icon: 'error',
        toast: true,
        position: 'center',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show a warning notification
function showWarning(message) {
    Swal.fire({
        title: 'Warning',
        text: message,
        icon: 'warning',
        toast: true,
        position: 'center',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show an info notification
function showInfo(message) {
    Swal.fire({
        title: 'Info',
        text: message,
        icon: 'info',
        toast: true,
        position: 'center',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show a confirmation dialog
function showConfirm(title, text, confirmButtonText = 'Yes', cancelButtonText = 'No') {
    return Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show a custom alert
function showCustomAlert(title, text, icon = 'info') {
    return Swal.fire({
        title: title,
        text: text,
        icon: icon,
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to show a loading alert
function showLoading(title = 'Loading...') {
    Swal.fire({
        title: title,
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        },
        width: '40%',
        customClass: {
            popup: 'swal2-large'
        }
    });
}

// Function to close any open alert
function closeAlert() {
    Swal.close();
} 