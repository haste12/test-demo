// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { 
    getAuth, 
    createUserWithEmailAndPassword, 
    signInWithEmailAndPassword, 
    sendEmailVerification, 
    sendPasswordResetEmail 
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";
import { 
    getFirestore, 
    setDoc, 
    doc, 
    collection, 
    addDoc, 
    serverTimestamp,
    getDoc,
    updateDoc 
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-firestore.js";

const firebaseConfig = {
    apiKey: "AIzaSyAjwt0a3WwFZh3ka6up3MDwMmdlkQzs34k",
    authDomain: "login-form-96501.firebaseapp.com",
    projectId: "login-form-96501",
    storageBucket: "login-form-96501.appspot.com",
    messagingSenderId: "5088309189",
    appId: "1:5088309189:web:5f331dec8180376217a5ac"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// More detailed message display function
function showMessage(message, divId, duration = 5000, isSuccess = false){
    console.log(`Showing message: ${message} in ${divId}`);
    var messageDiv = document.getElementById(divId);
    if (!messageDiv) {
        console.error(`Message div with id ${divId} not found`);
        return;
    }
    
    messageDiv.style.display = "block";
    messageDiv.innerHTML = message;
    messageDiv.style.opacity = 1;
    messageDiv.style.color = isSuccess ? "green" : "red";
    setTimeout(function(){
        messageDiv.style.opacity = 0;
    }, duration);
}

// Save message to Firestore
async function saveMessageToFirestore(userId, message, reply) {
    const db = getFirestore();
    try {
        await addDoc(collection(db, "chats"), {
            userId: userId,
            message: message,
            reply: reply,
            timestamp: serverTimestamp()
        });
        console.log("Message saved!");
    } catch (error) {
        console.error("Error saving message: ", error);
    }
}

// Sign Up Event Listener
const signUp = document.getElementById('submitSignUp');
signUp?.addEventListener('click', (event) => {
    event.preventDefault();
    const email = document.getElementById('rEmail').value;
    const password = document.getElementById('rPassword').value;
    const firstName = document.getElementById('fName').value;
    const lastName = document.getElementById('lName').value;

    const auth = getAuth();
    const db = getFirestore();

    createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
        const user = userCredential.user;
        
        // Send email verification
        return sendEmailVerification(user).then(async () => {
            // Create user data object
            const userData = {
                email: email,
                firstName: firstName,
                lastName: lastName,
                emailVerified: false,
                messageCount: 0,
                lastMessageTime: serverTimestamp(),
                lastResetTime: serverTimestamp(),
                dailyLimit: 10,  // Default message limit
                suspended: false
            };

            // Save user data to Firestore (single write operation)
            const userDocRef = doc(db, "users", user.uid);
            await setDoc(userDocRef, userData);

            return user;
        });
    })
    .then(() => {
        showMessage('Account Created. Please check your email for verification.', 'signUpMessage', 7000, true);
        
        // Redirect to verification guidance page
        setTimeout(() => {
            window.location.href = 'verify-email.html';
        }, 3000);
    })
    .catch((error) => {
        const errorCode = error.code;
        if (errorCode == 'auth/email-already-in-use') {
            showMessage('Email Address Already Exists !!!', 'signUpMessage');
        } else {
            showMessage('Unable to create User: ' + error.message, 'signUpMessage');
        }
    });
});

// Sign In Event Listener
const signIn = document.getElementById('submitSignIn');
signIn?.addEventListener('click', (event) => {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const auth = getAuth();

    signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
        const user = userCredential.user;
        
        if (user.emailVerified) {
            showMessage('Login is successful', 'signInMessage', 3000, true);
            localStorage.setItem('loggedInUserId', user.uid);
            window.location.href = 'homepage.html';
        } else {
            // Prevent login and show verification needed message
            showMessage('Please verify your email before logging in. Check your inbox or spam folder.', 'signInMessage', 7000);
            
            // Optionally, resend verification email
            sendEmailVerification(user)
            .then(() => {
                console.log('Verification email resent');
            })
            .catch((error) => {
                console.error('Error resending verification email', error);
            });
        }
    })
    .catch((error) => {
        const errorCode = error.code;
        if (errorCode === 'auth/invalid-credential') {
            showMessage('Incorrect Email or Password', 'signInMessage');
        } else {
            showMessage('Account does not Exist', 'signInMessage');
        }
    });
});

// Enhanced Forgot Password Function
function sendPasswordReset(email) {
    console.log(`Attempting to send password reset to: ${email}`);
    
    if (!email || email.trim() === '') {
        showMessage('Please enter a valid email address', 'forgotPasswordMessage');
        return Promise.reject(new Error('Email is empty'));
    }
    
    const actionCodeSettings = {
        url: window.location.origin + '/login.html',
        handleCodeInApp: false
    };
    
    return sendPasswordResetEmail(auth, email, actionCodeSettings)
        .then(() => {
            console.log('Password reset email sent successfully');
            return true;
        })
        .catch((error) => {
            console.error('Error sending password reset:', error);
            throw error;
        });
}

// Forgot Password Event Listener
const forgotPasswordBtn = document.getElementById('submitResetPassword');
if (forgotPasswordBtn) {
    console.log('Forgot password button found, adding event listener');
    
    forgotPasswordBtn.addEventListener('click', (event) => {
        event.preventDefault();
        console.log('Forgot password button clicked');
        
        const resetEmailInput = document.getElementById('resetEmail');
        if (!resetEmailInput) {
            console.error('Reset email input not found');
            return;
        }
        
        const email = resetEmailInput.value;
        console.log(`Attempting password reset for: ${email}`);
        
        sendPasswordReset(email)
            .then(() => {
                showMessage('Password reset email sent! Check your inbox and spam folder.', 'forgotPasswordMessage', 5000, true);
                
                // Optional: Return to sign in page after a few seconds
                setTimeout(() => {
                    const forgotPasswordForm = document.getElementById('forgotPassword');
                    const signInForm = document.getElementById('signIn');
                    
                    if (forgotPasswordForm && signInForm) {
                        forgotPasswordForm.style.display = 'none';
                        signInForm.style.display = 'block';
                    }
                }, 5000);
            })
            .catch((error) => {
                const errorCode = error.code;
                const errorMessage = error.message;
                console.error(`Password reset error: ${errorCode} - ${errorMessage}`);
                
                if (errorCode === 'auth/user-not-found') {
                    showMessage('No account exists with this email address.', 'forgotPasswordMessage');
                } else if (errorCode === 'auth/invalid-email') {
                    showMessage('Please enter a valid email address.', 'forgotPasswordMessage');
                } else if (errorCode === 'auth/missing-android-pkg-name' || 
                           errorCode === 'auth/missing-continue-uri' || 
                           errorCode === 'auth/missing-ios-bundle-id') {
                    showMessage('Configuration error. Please contact support.', 'forgotPasswordMessage');
                    console.error('Firebase configuration error:', error);
                } else {
                    showMessage(`Error sending reset email: ${errorMessage}`, 'forgotPasswordMessage');
                }
            });
    });
} else {

}

// Export the saveMessageToFirestore function to use in other scripts
export { saveMessageToFirestore };

// Make the reset password function globally available
window.sendPasswordReset = sendPasswordReset;



