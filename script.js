const signUpButton = document.getElementById('signUpButton');
const signInButton = document.getElementById('signInButton');
const signInForm = document.getElementById('signIn');
const signUpForm = document.getElementById('signup');

signUpButton.addEventListener('click', function() {
    signInForm.style.display = "none";
    signUpForm.style.display = "block";
    // Hide forgot password form if it exists
    const forgotPasswordForm = document.getElementById('forgotPassword');
    if (forgotPasswordForm) {
        forgotPasswordForm.style.display = "none";
    }
});

signInButton.addEventListener('click', function() {
    signInForm.style.display = "block";
    signUpForm.style.display = "none";
    // Hide forgot password form if it exists
    const forgotPasswordForm = document.getElementById('forgotPassword');
    if (forgotPasswordForm) {
        forgotPasswordForm.style.display = "none";
    }
});

// Add forgot password functionality
const forgotPasswordLink = document.getElementById('forgotPasswordLink');
if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', function(e) {
        e.preventDefault();
        const forgotPasswordForm = document.getElementById('forgotPassword');
        if (forgotPasswordForm) {
            signInForm.style.display = "none";
            signUpForm.style.display = "none";
            forgotPasswordForm.style.display = "block";
        }
    });
}

// Back to sign in from forgot password
const backToSignIn = document.getElementById('backToSignIn');
if (backToSignIn) {
    backToSignIn.addEventListener('click', function() {
        const forgotPasswordForm = document.getElementById('forgotPassword');
        if (forgotPasswordForm) {
            forgotPasswordForm.style.display = "none";
            signInForm.style.display = "block";
            signUpForm.style.display = "none";
        }
    });
}

// Function to clear message divs
function clearMessages() {
    const messageDivs = document.getElementsByClassName('messageDiv');
    for (let i = 0; i < messageDivs.length; i++) {
        messageDivs[i].style.display = 'none';
        messageDivs[i].innerHTML = '';
    }
}

// Add event listeners to form switch buttons to clear messages
if (signUpButton) signUpButton.addEventListener('click', clearMessages);
if (signInButton) signInButton.addEventListener('click', clearMessages);
if (forgotPasswordLink) forgotPasswordLink.addEventListener('click', clearMessages);
if (backToSignIn) backToSignIn.addEventListener('click', clearMessages);

// Function to handle AI chat
async function getAIResponse(message) {
    try {
        const userId = localStorage.getItem('loggedInUserId');
        if (!userId) {
            throw new Error('You need to be logged in to send messages');
        }

        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message,
                userId 
            }),
        });

        const data = await response.json();
        
        // Update remaining messages display
        if (data.remaining_messages) {
            updateRemainingMessages(data.remaining_messages);
        }

        if (response.status === 429) {
            throw new Error(data.error || 'Message limit reached. Please try again later.');
        }

        if (!response.ok) {
            throw new Error(data.error || 'Failed to get AI response');
        }

        if (data.reply) {
            return data.reply;
        } else if (data.error) {
            throw new Error(data.error);
        } else {
            throw new Error('Failed to get AI response');
        }
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Function to update remaining messages display
function updateRemainingMessages(message) {
    const remainingMessagesDiv = document.getElementById('remainingMessages');
    if (!remainingMessagesDiv) {
        // Create the div if it doesn't exist
        const div = document.createElement('div');
        div.id = 'remainingMessages';
        div.style.textAlign = 'right';
        div.style.padding = '10px';
        div.style.color = '#666';
        div.style.fontSize = '0.9em';
        div.style.backgroundColor = '#f5f5f5';
        div.style.borderRadius = '5px';
        div.style.margin = '10px 0';
        div.style.fontWeight = 'bold';
        
        // Insert before the chat input
        const inputContainer = document.querySelector('.input-container');
        if (inputContainer) {
            inputContainer.parentNode.insertBefore(div, inputContainer);
        }
    }
    
    if (remainingMessagesDiv) {
        remainingMessagesDiv.textContent = `📝 ${message}`;
        remainingMessagesDiv.style.display = 'block';
    }
}

// Function to check remaining messages on page load
async function checkRemainingMessages() {
    const userId = localStorage.getItem('loggedInUserId');
    if (!userId) return;

    try {
        const response = await fetch(`http://localhost:8000/remaining_messages/${userId}`);
        const data = await response.json();
        
        if (data.message) {
            updateRemainingMessages(data.message);
        }
    } catch (error) {
        console.error('Error checking remaining messages:', error);
    }
}

// Add event listener for chat form submission
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatResponse = document.getElementById('chatResponse');

if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        
        if (message) {
            try {
                chatResponse.innerHTML = 'Getting response...';
                const aiResponse = await getAIResponse(message);
                
                // Create a response container
                const responseHTML = `
                    <div class="ai-response">
                        <div class="response-content">${aiResponse}</div>
                    </div>
                `;
                
                chatResponse.innerHTML = responseHTML;
                chatInput.value = '';
            } catch (error) {
                chatResponse.innerHTML = `
                    <div class="error-message">
                        <span style="color: #dc3545;">❌ Error:</span> ${error.message}
                    </div>
                `;
            }
        }
    });
}

// Check remaining messages when page loads
document.addEventListener('DOMContentLoaded', checkRemainingMessages);

// Check remaining messages on page load and update every minute
async function updateRemainingMessagesPeriodically() {
    const userId = localStorage.getItem('loggedInUserId');
    if (!userId) return;

    try {
        const response = await fetch(`http://localhost:8000/remaining_messages/${userId}`);
        const data = await response.json();
        
        if (data.message) {
            updateRemainingMessages(data.message);
        }
    } catch (error) {
        console.error('Error checking remaining messages:', error);
    }
}

// Update remaining messages display periodically
setInterval(updateRemainingMessagesPeriodically, 60000); // Update every minute

// Initial check when page loads
document.addEventListener('DOMContentLoaded', updateRemainingMessagesPeriodically);