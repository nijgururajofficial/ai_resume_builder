// Firebase Imports
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import {
    getAuth,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signOut,
    onAuthStateChanged,
    GoogleAuthProvider,
    signInWithPopup
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";
import {
    getStorage,
    ref,
    uploadBytes,
    listAll,
    getDownloadURL,
    deleteObject
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-storage.js";
// NEW: Firestore Imports
import {
    getFirestore,
    doc,
    onSnapshot,
    setDoc,
    updateDoc,
    increment,
    getDoc // Import getDoc for one-time read
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";


// IMPORTANT: Replace with your Firebase project's configuration
const firebaseConfig = {
        apiKey: "AIzaSyDjbhfIqFhLVzqbPf3SximwS7yDSPR0iYQ",
        authDomain: "fastapi-78c3d.firebaseapp.com",
        projectId: "fastapi-78c3d",
        storageBucket: "fastapi-78c3d.firebasestorage.app",
        messagingSenderId: "168845832927",
        appId: "1:168845832927:web:03b236cdb4ec136e9a6f6a",
        measurementId: "G-LGD0WSM8NK"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const storage = getStorage(app);
// NEW: Initialize Firestore
const db = getFirestore(app);

// DOM Elements
const authContainer = document.getElementById('auth-container');
const dashboard = document.getElementById('dashboard');
const authForm = document.getElementById('auth-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submit-btn');
const toggleAuthLink = document.getElementById('toggle-auth');
const authTitle = document.getElementById('auth-title');
const logoutBtn = document.getElementById('logout-btn');
const userEmailSpan = document.getElementById('user-email');
const userIdSpan = document.getElementById('user-id');
const errorMessageDiv = document.getElementById('error-message');
const errorTextSpan = document.getElementById('error-text');
const fetchPublicBtn = document.getElementById('fetch-public');
const fetchProtectedBtn = document.getElementById('fetch-protected');
const responseContent = document.getElementById('response-content');
const googleSignInBtn = document.getElementById('google-signin-btn');
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const fileListDiv = document.getElementById('file-list');
const deleteModal = document.getElementById('delete-modal');
const deleteModalText = document.getElementById('delete-modal-text');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
const cancelDeleteBtn = document.getElementById('cancel-delete-btn');

// NEW: Credit display element
const userCreditsSpan = document.getElementById('user-credits');


// State
let isLogin = true;
let fileToDeleteRef = null;
// NEW: State for credits and to manage Firestore listener
let currentUserCredits = 0;
let unsubscribeCredits = null; // To stop listening for credit changes on logout


// FastAPI Backend URL
const FASTAPI_BASE_URL = 'http://127.0.0.1:8000';

// --- Firebase Auth State Listener ---
onAuthStateChanged(auth, user => {
    if (user) {
        showDashboard(user);
    } else {
        showAuthForm();
    }
});

// --- UI Update Functions ---
function showDashboard(user) {
    authContainer.classList.add('hidden');
    dashboard.classList.remove('hidden');
    userEmailSpan.textContent = user.email;
    userIdSpan.textContent = user.uid;
    displayUserFiles();
    // NEW: Start listening for credit updates
    setupCreditListener(user);
}

function showAuthForm() {
    authContainer.classList.remove('hidden');
    dashboard.classList.add('hidden');
    responseContent.textContent = 'Click a button to fetch data...';
    // NEW: Stop listening for credits when user logs out
    if (unsubscribeCredits) {
        unsubscribeCredits();
    }
}
function toggleAuthMode(){isLogin=!isLogin;authTitle.textContent=isLogin?"Login":"Sign Up";submitBtn.textContent=isLogin?"Login":"Sign Up";toggleAuthLink.textContent=isLogin?"Need an account? Sign Up":"Have an account? Login";hideError();authForm.reset()}function showError(e){errorTextSpan.textContent=e;errorMessageDiv.classList.remove("hidden")}function hideError(){errorMessageDiv.classList.add("hidden")}


// --- Event Listeners ---
toggleAuthLink.addEventListener('click',e=>{e.preventDefault();toggleAuthMode()});

// MODIFIED: Auth form to handle new user credit creation
authForm.addEventListener('submit',async e=>{
    e.preventDefault();
    hideError();
    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        if (isLogin) {
            await signInWithEmailAndPassword(auth, email, password);
        } else {
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            // After creating the user, immediately create their credit document
            await createUserCreditDocument(userCredential.user);
        }
    } catch (error) {
        console.error("Authentication error:", error.message);
        showError(error.message);
    }
});

// MODIFIED: Google sign-in to handle new user credit creation
googleSignInBtn.addEventListener('click',async()=>{
    hideError();
    const provider = new GoogleAuthProvider;
    try {
        const result = await signInWithPopup(auth, provider);
        const userDocRef = doc(db, 'users', result.user.uid);
        const docSnap = await getDoc(userDocRef);
        // If the user document does not exist, it's their first time signing in with Google
        if (!docSnap.exists()) {
            await createUserCreditDocument(result.user);
        }
    } catch (error) {
        console.error("Google Sign-In error:", error);
        showError(error.message);
    }
});

logoutBtn.addEventListener('click',async()=>{try{await signOut(auth)}catch(e){console.error("Logout error:",e.message);showError("Failed to log out. Please try again.")}});


// --- NEW: Firestore Credit Management ---

// This function is now called explicitly on sign-up
async function createUserCreditDocument(user) {
    const userDocRef = doc(db, 'users', user.uid);
    try {
        await setDoc(userDocRef, { credits: 5 });
        console.log("New user document created with 5 credits.");
    } catch (err) {
        console.error("Error creating user document:", err);
    }
}

function setupCreditListener(user) {
    const userDocRef = doc(db, 'users', user.uid);

    unsubscribeCredits = onSnapshot(userDocRef, (snapshot) => {
        if (snapshot.exists()) {
            const userData = snapshot.data();
            currentUserCredits = userData.credits;
            userCreditsSpan.textContent = currentUserCredits.toFixed(2);
            updateUploadUI(); // Update the button state based on credits
        } else {
            // This case handles users who existed before the credit system was implemented.
            console.log("User document doesn't exist, creating one.");
            createUserCreditDocument(user);
        }
    });
}

function updateUploadUI() {
    if (currentUserCredits <= 0) {
        uploadBtn.disabled = true;
        uploadBtn.classList.add('opacity-50', 'cursor-not-allowed');
        uploadBtn.title = "You have no credits left.";
        fileInput.disabled = true;
        uploadStatus.textContent = "No credits left. Buy more to upload.";
        uploadStatus.className = 'mt-4 text-sm text-red-500';
    } else {
        uploadBtn.disabled = false;
        uploadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        uploadBtn.title = "";
        fileInput.disabled = false;
        uploadStatus.textContent = ""; // Clear status on refresh
    }
}


// --- Firebase Storage Functions ---

async function displayUserFiles(){const e=auth.currentUser;if(e){fileListDiv.innerHTML='<p class="text-gray-500">Loading your files...</p>';const t=ref(storage,`users/${e.uid}`);try{const e=await listAll(t);if(fileListDiv.innerHTML="",0===e.items.length){fileListDiv.innerHTML='<p class="text-gray-500">You have not uploaded any files yet.</p>';return}for(const t of e.items){const e=await getDownloadURL(t),n=document.createElement("div");n.className="flex items-center justify-between";const o=document.createElement("a");o.href=e,o.target="_blank",o.textContent=t.name,o.className="text-blue-600 hover:text-blue-800 hover:underline";const i=document.createElement("button");i.innerHTML="&times;",i.className="text-red-500 hover:text-red-700 font-bold text-xl ml-4 px-2 rounded",i.title=`Delete ${t.name}`,i.addEventListener("click",()=>showDeleteConfirm(t)),n.appendChild(o),n.appendChild(i),fileListDiv.appendChild(n)}}catch(e){console.error("Error listing files:",e),fileListDiv.innerHTML='<p class="text-red-500">Could not load your files.</p>'}}}

// MODIFIED: Event Listener for the Upload Button
uploadBtn.addEventListener('click', async () => {
    const user = auth.currentUser;
    const file = fileInput.files[0];

    // Check for user, file, AND credits before proceeding
    if (!user) {
        uploadStatus.textContent = 'You must be logged in to upload files.';
        return;
    }
    if (currentUserCredits <= 0) {
        uploadStatus.textContent = 'You do not have enough credits to upload.';
        return;
    }
    if (!file) {
        uploadStatus.textContent = 'Please select a file to upload.';
        return;
    }

    const filePath = `users/${user.uid}/${file.name}`;
    const fileRef = ref(storage, filePath);

    try {
        uploadStatus.textContent = `Uploading ${file.name}...`;
        uploadStatus.className = 'mt-4 text-sm text-blue-500';

        await uploadBytes(fileRef, file);

        uploadStatus.textContent = 'Upload complete! Deducting credits...';
        uploadStatus.className = 'mt-4 text-sm text-green-500';

        // NEW: Deduct credits after successful upload
        const userDocRef = doc(db, 'users', user.uid);
        await updateDoc(userDocRef, {
            credits: increment(-0.25)
        });

        fileInput.value = '';
        await displayUserFiles();

    } catch (error) {
        console.error("Upload Error:", error);
        uploadStatus.textContent = `Upload failed: ${error.code} - ${error.message}`;
        uploadStatus.className = 'mt-4 text-sm text-red-500';
    }
});


// --- Delete Confirmation Modal Functions ---
function showDeleteConfirm(e){fileToDeleteRef=e,deleteModalText.textContent=`Are you sure you want to delete '${e.name}'?`,deleteModal.classList.remove("hidden")}function hideDeleteConfirm(){fileToDeleteRef=null,deleteModal.classList.add("hidden")}
confirmDeleteBtn.addEventListener('click', async () => {
    if (!fileToDeleteRef) return;

    try {
        await deleteObject(fileToDeleteRef);
        hideDeleteConfirm();
        await displayUserFiles();
    } catch (error) {
        console.error("Error deleting file:", error);
        hideDeleteConfirm();
        alert(`Failed to delete file: ${error.message}`);
    }
});
cancelDeleteBtn.addEventListener('click', hideDeleteConfirm);


// --- API Fetching Functions ---
async function fetchApi(e,t=!1){try{console.log(`Making ${t?"authenticated":"public"} request to: ${FASTAPI_BASE_URL}${e}`);const n={"Content-Type":"application/json"};if(t){const e=auth.currentUser;if(!e)throw new Error("You must be logged in to access this resource.");const t=await e.getIdToken(!0);n.Authorization=`Bearer ${t}`}const o=await fetch(`${FASTAPI_BASE_URL}${e}`,{method:"GET",headers:n,mode:"cors",credentials:"omit"});if(!o.ok){const e=await o.text();let t;try{t=JSON.parse(e)}catch{t={detail:e}}throw new Error(t.detail||`HTTP error! status: ${o.status}`)}const s=await o.json();responseContent.textContent=JSON.stringify(s,null,2)}catch(e){console.error("API Fetch-Fehler:",e);responseContent.textContent=`Fehler: ${e.message}`}}
fetchPublicBtn.addEventListener('click', () => fetchApi('/'));
fetchProtectedBtn.addEventListener('click', () => fetchApi('/api/protected', true));
