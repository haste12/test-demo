import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { getFirestore, doc, getDoc } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-firestore.js";

// Initialize (idempotent if already initialized elsewhere, guarded)
const firebaseConfig = {
  apiKey: "AIzaSyAjwt0a3WwFZh3ka6up3MDwMmdlkQzs34k",
  authDomain: "login-form-96501.firebaseapp.com",
  projectId: "login-form-96501",
  storageBucket: "login-form-96501.appspot.com",
  messagingSenderId: "5088309189",
  appId: "1:5088309189:web:5f331dec8180376217a5ac"
};

let app;
try {
  app = initializeApp(firebaseConfig);
} catch (e) {
  // App likely already initialized – ignore
}
const db = getFirestore();

async function loadUserName(userId){
  try {
    if(!userId) return null;
    const snap = await getDoc(doc(db,'users',userId));
    if (snap.exists()) {
      const data = snap.data();
      return data.firstName || data.lastName ? `${data.firstName || ''} ${data.lastName || ''}`.trim() : (data.email || null);
    }
  } catch(err){
    console.warn('Failed to load user name', err);
  }
  return null;
}

export async function maybeShowGreeting(){
  const chatbox = document.getElementById('chatbox');
  const greetingContainer = document.getElementById('greetingContainer');
  if(!chatbox || !greetingContainer) return;

  // If chat already has messages (history loaded), skip greeting
  if (chatbox.children.length > 0) return;

  const userId = localStorage.getItem('loggedInUserId');
  let name = await loadUserName(userId);
  if(!name) name = 'User';
  const titleEl = document.getElementById('greetingTitle');
  if (titleEl) titleEl.textContent = `Hello dear ${name}`;
  greetingContainer.style.display = 'block';
}

export function hideGreeting(){
  const greetingContainer = document.getElementById('greetingContainer');
  if (greetingContainer) greetingContainer.style.display = 'none';
}

// Auto attempt after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  maybeShowGreeting();
});
