// Standalone verification polling script
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { getAuth, onAuthStateChanged, sendEmailVerification } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAjwt0a3WwFZh3ka6up3MDwMmdlkQzs34k",
  authDomain: "login-form-96501.firebaseapp.com",
  projectId: "login-form-96501",
  storageBucket: "login-form-96501.appspot.com",
  messagingSenderId: "5088309189",
  appId: "1:5088309189:web:5f331dec8180376217a5ac"
};

initializeApp(firebaseConfig);
const auth = getAuth();

const statusEl = document.getElementById('verificationStatus');
const resendBtn = document.getElementById('resendVerification');
const backBtn = document.getElementById('backToLogin');

function setStatus(msg, success=false){
  if (statusEl){
    statusEl.textContent = msg;
    statusEl.style.color = success ? 'green' : '#333';
  }
  console.log('[VerifyEmail]', msg);
}

let pollIntervalId = null;
function startPolling(){
  if (pollIntervalId) return;
  pollIntervalId = setInterval(async () => {
    const user = auth.currentUser;
    if (!user) return;
    try {
      await user.reload();
      if (user.emailVerified){
        setStatus('Email verified! Redirecting...', true);
        clearInterval(pollIntervalId);
        setTimeout(()=>{ window.location.href = 'homepage.html'; }, 1500);
      }
    } catch(e){
      console.warn('Reload failed during polling', e);
    }
  }, 4000);
}

onAuthStateChanged(auth, user => {
  if (!user){
    setStatus('No signed in user. Returning to login...');
    setTimeout(()=> window.location.href = 'index.html', 2000);
  } else {
    if (user.emailVerified){
      setStatus('Already verified. Redirecting...', true);
      setTimeout(()=> window.location.href = 'homepage.html', 1200);
    } else {
      setStatus('Waiting for you to click the verification link in your email.');
      startPolling();
    }
  }
});

resendBtn?.addEventListener('click', async () => {
  const user = auth.currentUser;
  if (!user){
    setStatus('No user to verify.');
    return;
  }
  try {
    await sendEmailVerification(user);
    setStatus('Verification email sent again. Check inbox/spam.');
  } catch (e){
    setStatus('Failed to send verification email: '+ e.message);
  }
});

backBtn?.addEventListener('click', () => {
  window.location.href = 'index.html';
});
