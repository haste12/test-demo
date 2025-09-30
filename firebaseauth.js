// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { 
    getAuth, 
    GoogleAuthProvider,
    signInWithPopup,
    signInWithEmailAndPassword
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
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

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



// Email verification removed: resend button intentionally disabled

// Export the saveMessageToFirestore function to use in other scripts
export { saveMessageToFirestore };

// Email/password login (existing legacy users) - No signup or reset UI
const submitSignIn = document.getElementById('submitSignIn');
submitSignIn?.addEventListener('click', (e)=>{
        e.preventDefault();
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        if(!emailInput || !passwordInput) return;
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        if(!email || !password){
                showMessage('Enter email and password','signInMessage');
                return;
        }
        signInWithEmailAndPassword(auth, email, password)
            .then((cred)=>{
                localStorage.setItem('loggedInUserId', cred.user.uid);
                showMessage('Login successful','signInMessage',1500,true);
                setTimeout(()=>{ window.location.href='homepage.html'; },500);
            })
            .catch(err=>{
                let msg='Login failed';
                if (err.code === 'auth/invalid-credential' || err.code === 'auth/wrong-password') msg='Incorrect email or password';
                else if (err.code === 'auth/user-not-found') msg='Account not found';
                else if (err.code === 'auth/too-many-requests') msg='Too many attempts. Try again later.';
                showMessage(msg,'signInMessage');
            });
});

// Google Sign In / Sign Up (single flow)
async function handleGoogleAuth(buttonSource){
    try {
        const result = await signInWithPopup(auth, googleProvider);
        const user = result.user;

        // Check if user document exists
        const userRef = doc(db, 'users', user.uid);
        const snap = await getDoc(userRef);
        if (!snap.exists()) {
            // Create initial user document
            const displayName = user.displayName || '';
            let firstName = '';
            let lastName = '';
            if (displayName) {
                const parts = displayName.split(' ');
                firstName = parts[0];
                lastName = parts.slice(1).join(' ');
            }
            await setDoc(userRef, {
                email: user.email,
                firstName,
                lastName,
                emailVerified: true,
                messageCount: 0,
                lastMessageTime: serverTimestamp(),
                lastResetTime: serverTimestamp(),
                dailyLimit: 10,
                suspended: false,
                provider: 'google'
            });
        }

        localStorage.setItem('loggedInUserId', user.uid);
        window.location.href = 'homepage.html';
    } catch (error) {
        console.error('Google auth error:', error);
        const msgDiv = document.getElementById('signInMessage') || document.getElementById('signUpMessage');
        let friendly = 'Google sign-in failed';
        if (error.code === 'auth/operation-not-allowed') {
            friendly = 'Google sign-in is not enabled. Enable Google provider in Firebase Console > Authentication > Sign-in method.';
        } else if (error.code === 'auth/popup-blocked') {
            friendly = 'Popup was blocked by the browser. Allow popups and try again.';
        } else if (error.code === 'auth/cancelled-popup-request') {
            friendly = 'Popup closed before completing sign-in.';
        } else if (error.code === 'auth/popup-closed-by-user') {
            friendly = 'Popup closed. Please try again.';
        } else if (error.code === 'auth/network-request-failed') {
            friendly = 'Network error. Check your connection.';
        }
        if (msgDiv) {
            msgDiv.style.display = 'block';
            msgDiv.style.color = 'red';
            msgDiv.textContent = friendly;
            setTimeout(()=> msgDiv.style.display='none', 8000);
        }
    }
}

document.getElementById('googleSignIn')?.addEventListener('click', (e)=>{ e.preventDefault(); handleGoogleAuth('signin'); });




