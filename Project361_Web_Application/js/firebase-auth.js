// Firebase Authentication
// Project361 Heart Rate Analytics

import {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updateProfile,
    sendPasswordResetEmail
} from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";

import { auth } from "./firebase-config.js";

// =========================
// LOGIN
// =========================
const loginForm = document.getElementById("loginForm");

if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const message = document.getElementById("loginMessage");

        try {
            await signInWithEmailAndPassword(auth, email, password);
            message.textContent = "Login successful! Redirecting...";

            setTimeout(() => {
                window.location.replace("index.html");
            }, 700);
        } catch (error) {
            console.error(error);
            message.textContent = getAuthErrorMessage(error);
        }
    });
}

// =========================
// FORGOT PASSWORD
// =========================
const forgotPasswordLink = document.getElementById("forgotPasswordLink");

if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener("click", async function (event) {
        event.preventDefault();

        const emailInput = document.getElementById("email");
        const message = document.getElementById("loginMessage");
        const email = emailInput.value.trim();

        if (!email) {
            message.textContent = "Please enter your email address first.";
            emailInput.focus();
            return;
        }

        try {
            await sendPasswordResetEmail(auth, email);
            message.textContent = "Password reset email sent. Please check your inbox (and spam folder).";
        } catch (error) {
            console.error("Password reset error:", error);
            message.textContent = getAuthErrorMessage(error);
        }
    });
}

// =========================
// SIGN UP
// =========================
const signupForm = document.getElementById("signupForm");

if (signupForm) {
    signupForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const name = document.getElementById("name").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirmPassword").value;
        const message = document.getElementById("signupMessage");

        if (password !== confirmPassword) {
            message.textContent = "Passwords do not match.";
            return;
        }

        try {
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                email,
                password
            );

            await updateProfile(userCredential.user, {
                displayName: name
            });

            message.textContent = "Account created successfully!";

            setTimeout(() => {
                window.location.replace("index.html");
            }, 700);
        } catch (error) {
            console.error(error);
            message.textContent = getAuthErrorMessage(error);
        }
    });
}

// =========================
// FIREBASE ERROR MESSAGES
// =========================
function getAuthErrorMessage(error) {
    switch (error.code) {
        case "auth/invalid-credential":
            return "Incorrect email or password.";
        case "auth/email-already-in-use":
            return "An account with this email already exists.";
        case "auth/weak-password":
            return "Password should be at least 6 characters.";
        case "auth/invalid-email":
            return "Please enter a valid email address.";
        case "auth/user-not-found":
            return "No account was found with this email.";
        case "auth/wrong-password":
            return "Incorrect password.";
        case "auth/too-many-requests":
            return "Too many attempts. Please wait a moment and try again.";
        case "auth/network-request-failed":
            return "Network error. Please check your internet connection.";
        default:
            return "Something went wrong. Please try again.";
    }
}
