import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { 
    getAuth, 
    createUserWithEmailAndPassword 
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";
import { 
    getFirestore,
    doc,
    setDoc
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-firestore.js";

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
const db = getFirestore(app);

async function createAdminUser() {
    try {
        // Create admin user
        const userCredential = await createUserWithEmailAndPassword(auth, "admin@lfu.edu", "Admin@123");
        const uid = userCredential.user.uid;

        // Set admin data in Firestore
        await setDoc(doc(db, "users", uid), {
            email: "admin@lfu.edu",
            firstName: "Admin",
            lastName: "LFU",
            isAdmin: true,
            createdAt: new Date(),
            lastActive: new Date()
        });

        console.log("Admin user created successfully!");
        console.log("Email: admin@lfu.edu");
        console.log("Password: Admin@123");
    } catch (error) {
        console.error("Error creating admin user:", error);
    }
}

// Create the admin user
createAdminUser(); 