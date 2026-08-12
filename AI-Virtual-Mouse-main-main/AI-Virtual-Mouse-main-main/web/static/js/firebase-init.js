// Firebase initialization using the installed `firebase` package
import { initializeApp } from 'firebase/app';
import { getAnalytics } from 'firebase/analytics';

const firebaseConfig = {
  apiKey: "AIzaSyAeBwxo9ScRuJ1x_7GQJDvFG0pUk4Lo1GY",
  authDomain: "apphand-f453b.firebaseapp.com",
  projectId: "apphand-f453b",
  storageBucket: "apphand-f453b.firebasestorage.app",
  messagingSenderId: "855591971514",
  appId: "1:855591971514:web:7b44fdb5ccd3f41a00f083",
  measurementId: "G-T0QRD6E9Z8"
};

const app = initializeApp(firebaseConfig);
try {
  const analytics = getAnalytics(app);
  console.log('Firebase analytics initialized');
} catch (e) {
  // analytics may fail in some browsers or non-HTTPS contexts
  console.warn('Firebase analytics not available', e);
}

export default app;
