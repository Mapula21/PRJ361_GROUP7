import { initializeApp, getApps, getApp } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";

const firebaseConfig = {
    apiKey: "AIzaSyDTqfb-1wJmSxRSHEN7SmhRXZAO8AqzzvI",
    authDomain: "prj361-3434e.firebaseapp.com",
    databaseURL: "https://prj361-3434e-default-rtdb.firebaseio.com",
    projectId: "prj361-3434e",
    storageBucket: "prj361-3434e.firebasestorage.app",
    messagingSenderId: "558383925397",
    appId: "1:558383925397:web:022c8599f0df694eb8f39c"
};

const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
const auth = getAuth(app);

export { app, auth };
