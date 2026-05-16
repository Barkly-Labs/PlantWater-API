importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js");

firebase.initializeApp({
    apiKey: "AIzaSyBuGuSBZ59OyNlXO6msoY9XwJMZtirO3b0",
    authDomain: "smart-garden-4d476.firebaseapp.com",
    projectId: "smart-garden-4d476",
    storageBucket: "smart-garden-4d476.firebasestorage.app",
    messagingSenderId: "213616042233",
    appId: "1:213616042233:web:45360b3c4e2ef15ddb4228",
]   vapidKey: "YOUR_PUBLIC_VAPID_KEY"
});

const messaging = firebase.messaging();

// ✅ Background notifications (modern)
messaging.onBackgroundMessage((payload) => {
    console.log("📩 Background message received:", payload);

    const title = payload?.notification?.title || "Smart Garden";
    const body = payload?.notification?.body || "";

    self.registration.showNotification(title, {
        body,
        icon: "/static/icon.png"
    });
});