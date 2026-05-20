importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js");

firebase.initializeApp({
    apiKey: "AIzaSyBuGuSBZ59OyNlXO6msoY9XwJMZtirO3b0",
    authDomain: "smart-garden-4d476.firebaseapp.com",
    projectId: "smart-garden-4d476",
    storageBucket: "smart-garden-4d476.firebasestorage.app",
    messagingSenderId: "213616042233",
    appId: "1:213616042233:web:45360b3c4e2ef15ddb4228",
    measurementId: "G-SY1BBH1LLJ"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    console.log("🔥 SW ACTIVE AND LISTENING");
    console.log("📩 Service Worker: Background message received", payload);

    try {
        const title =
            payload?.notification?.title ||
            payload?.data?.title ||
            "🌿 Smart Garden";

        const body =
            payload?.notification?.body ||
            payload?.data?.body ||
            "You have a new alert";

        const notificationOptions = {
            body: body,
            icon: "/static/icon.png",
            badge: "/static/icon.png",
            tag: "garden-notification",
            requireInteraction: true,
            data: payload?.data || {}
        };

        console.log("📲 Service Worker: Showing notification", { title, ...notificationOptions });

        self.registration.showNotification(title, notificationOptions)
            .then(() => {
                console.log("✅ Service Worker: Notification displayed successfully");
            })
            .catch((err) => {
                console.error("❌ Service Worker: Failed to show notification", err);
            });

    } catch (err) {
        console.error("❌ Service Worker: Error in onBackgroundMessage handler", err);
    }
});

console.log("✅ Service Worker: Firebase messaging initialized");