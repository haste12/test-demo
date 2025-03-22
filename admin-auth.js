import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { 
    getAuth,
    signInWithEmailAndPassword,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";

const firebaseConfig = {
    apiKey: "AIzaSyAjwt0a3WwFZh3ka6up3MDwMmdlkQzs34k",
    authDomain: "login-form-96501.firebaseapp.com",
    projectId: "login-form-96501",
    storageBucket: "login-form-96501.appspot.com",
    messagingSenderId: "5088309189",
    appId: "1:5088309189:web:5f331dec8180376217a5ac"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Admin email constant
const ADMIN_EMAIL = "admin@lfu.edu";

// Check if user is an admin
function isAdmin(email) {
    return email === ADMIN_EMAIL;
}

// Handle admin sign in
document.getElementById('submitAdminSignIn').addEventListener('click', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('adminEmail').value;
    const password = document.getElementById('adminPassword').value;
    const messageDiv = document.getElementById('adminSignInMessage');
    
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        
        if (isAdmin(email)) {
            localStorage.setItem('adminId', userCredential.user.uid);
            localStorage.setItem('adminEmail', email);
            window.location.href = 'admin-dashboard.html';
        } else {
            messageDiv.style.display = 'block';
            messageDiv.style.color = '#dc3545';
            messageDiv.textContent = 'Access denied. Admin privileges required.';
            auth.signOut();
        }
    } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.style.color = '#dc3545';
        messageDiv.textContent = 'Invalid email or password.';
    }
});

// Check authentication state
onAuthStateChanged(auth, async (user) => {
    if (user) {
        if (!isAdmin(user.email) && window.location.pathname.includes('admin-dashboard.html')) {
            window.location.href = 'admin-login.html';
        }
    } else if (window.location.pathname.includes('admin-dashboard.html')) {
        window.location.href = 'admin-login.html';
    }
}); 