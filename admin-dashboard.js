import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { 
    getAuth,
    signOut,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";
import { 
    getFirestore,
    collection,
    getDocs,
    query,
    where,
    updateDoc,
    doc,
    deleteDoc
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

// Admin email constant
const ADMIN_EMAIL = "admin@lfu.edu";

// Check if user is admin
function isAdmin(email) {
    return email === ADMIN_EMAIL;
}

// Load dashboard data
async function loadDashboardData() {
    try {
        // Get all users except admin
        const usersQuery = query(collection(db, "users"), where("email", "!=", ADMIN_EMAIL));
        const usersSnapshot = await getDocs(usersQuery);
        const users = [];
        
        // Get all chats for message counting
        const chatsQuery = query(collection(db, "chats"));
        const chatsSnapshot = await getDocs(chatsQuery);
        const chats = chatsSnapshot.docs.map(doc => doc.data());

        // Process users and their messages
        usersSnapshot.forEach(doc => {
            const userData = { id: doc.id, ...doc.data() };
            
            // Count messages for this user
            const userMessages = chats.filter(chat => chat.userId === doc.id);
            const messagesToday = userMessages.filter(chat => {
                const timestamp = chat.timestamp?.toDate();
                return timestamp && timestamp > new Date(Date.now() - 86400000);
            }).length;

            // Only include users who have sent messages
            if (userMessages.length > 0) {
                users.push({
                    ...userData,
                    totalMessages: userMessages.length,
                    messagesToday: messagesToday,
                    dailyLimit: userData.dailyLimit === null ? 'Unlimited' : (userData.dailyLimit || 0)
                });
            }
        });

        // Update statistics
        document.getElementById('totalUsers').textContent = users.length;
        document.getElementById('activeUsers').textContent = users.filter(user => user.lastActive > Date.now() - 86400000).length;
        document.getElementById('totalMessages').textContent = chats.length;
        document.getElementById('messagesToday').textContent = chats.filter(chat => {
            const timestamp = chat.timestamp?.toDate();
            return timestamp && timestamp > new Date(Date.now() - 86400000);
        }).length;

        // Populate users table
        const tableBody = document.getElementById('usersTableBody');
        tableBody.innerHTML = '';

        if (users.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="7" style="text-align: center; padding: 20px;">
                    No users have sent messages yet.
                </td>
            `;
            tableBody.appendChild(row);
        } else {
            // Sort users by total messages (highest to lowest)
            users.sort((a, b) => b.totalMessages - a.totalMessages);

            users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.firstName || ''} ${user.lastName || ''}</td>
                    <td>${user.email}</td>
                    <td>
                        Total: ${user.totalMessages}<br>
                        Today: ${user.messagesToday}<br>
                        Daily Limit: ${user.dailyLimit}
                    </td>
                    <td>${user.lastActive > Date.now() - 86400000 ? 
                        '<span style="color: #22c55e;">Active</span>' : 
                        '<span style="color: #ef4444;">Inactive</span>'}
                    </td>
                    <td>${user.suspended ? 
                        '<span style="color: #ef4444;">Suspended</span>' : 
                        '<span style="color: #22c55e;">Active</span>'}
                    </td>
                    <td>
                        <div class="limit-control">
                            <input type="number" 
                                   id="limit-${user.id}" 
                                   value="${user.dailyLimit === 'Unlimited' ? '' : user.dailyLimit}" 
                                   min="0" 
                                   class="limit-input"
                                   style="width: 80px; padding: 4px; margin-right: 8px;"
                            >
                            <button class="btn btn-primary" 
                                    onclick="updateLimit('${user.id}', this)">
                                Update Limit
                            </button>
                        </div>
                    </td>
                    <td>
                        <button class="btn ${user.suspended ? 'btn-success' : 'btn-warning'}" 
                                onclick="suspendUser('${user.id}', ${!user.suspended})">
                            ${user.suspended ? 'Unsuspend' : 'Suspend'}
                        </button>
                        <button class="btn btn-danger" onclick="deleteUser('${user.id}')">Delete</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

// Handle user suspension
window.suspendUser = async (userId, suspend) => {
    try {
        const userRef = doc(db, "users", userId);
        await updateDoc(userRef, {
            suspended: suspend
        });
        loadDashboardData();
    } catch (error) {
        console.error("Error updating user suspension:", error);
    }
};

// Handle message limit update
window.updateLimit = async (userId, button) => {
    const inputElement = button.previousElementSibling;
    const newLimit = parseInt(inputElement.value);
    
    // Validate input
    if (isNaN(newLimit) || newLimit < 0) {
        alert('Please enter a valid number (0 or greater)');
        return;
    }

    try {
        const userRef = doc(db, "users", userId);
        
        // Set the exact new limit (null for unlimited if 0) and reset message count
        await updateDoc(userRef, {
            dailyLimit: newLimit === 0 ? null : newLimit,
            messageCount: 0,  // Reset message count to 0
            lastResetTime: new Date()  // Reset the timer
        });

        alert('Message limit updated successfully');
        loadDashboardData(); // Refresh the display
    } catch (error) {
        console.error('Error updating limit:', error);
        alert('Error updating limit');
    }
};

// Handle user deletion
window.deleteUser = async (userId) => {
    if (confirm("Are you sure you want to delete this user? This action cannot be undone.")) {
        try {
            await deleteDoc(doc(db, "users", userId));
            loadDashboardData();
        } catch (error) {
            console.error("Error deleting user:", error);
        }
    }
};

// Handle admin logout
document.getElementById('adminLogout').addEventListener('click', async () => {
    try {
        await signOut(auth);
        localStorage.removeItem('adminId');
        localStorage.removeItem('adminEmail');
        window.location.href = 'admin-login.html';
    } catch (error) {
        console.error("Error signing out:", error);
    }
});

// Check authentication and admin status
onAuthStateChanged(auth, async (user) => {
    if (user) {
        if (isAdmin(user.email)) {
            document.getElementById('adminEmail').textContent = user.email;
            loadDashboardData();
        } else {
            window.location.href = 'admin-login.html';
        }
    } else {
        window.location.href = 'admin-login.html';
    }
}); 