// 1️⃣ Initialize Firebase
const firebaseConfig = {
  apiKey: "AIzaSyB-Xve-6sZQLxpYUt3GXl4svafoU06095o",
  authDomain: "hack-job-958fe.firebaseapp.com",
  projectId: "hack-job-958fe",
  storageBucket: "hack-job-958fe.appspot.com",
  messagingSenderId: "967253891072",
  appId: "1:967253891072:web:84e092e268115d120ee0e5",
  measurementId: "G-4Z7Q285FG5"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// 2️⃣ Get container element
const hackathonsContainer = document.getElementById('hackathons');

// 3️⃣ Fetch & render
db.collection('hackathons').get().then(snapshot => {
  snapshot.forEach(doc => {
    const data = doc.data();

    const card = document.createElement('div');
    card.className = 'card';

    card.innerHTML = `
      <h3>${data.title}</h3>
      <p><strong>Host:</strong> ${data.host || 'N/A'}</p>
      <p><strong>Days Left:</strong> ${data.days_left}</p>
      <p><strong>Prize:</strong> ${data.prize}</p>
      <p><strong>Participants:</strong> ${data.participants || 'N/A'}</p>
      <p><strong>Submission Period:</strong> ${data.submission_period}</p>
      <p><strong>Themes:</strong> ${data.themes && data.themes.length > 0 ? data.themes.join(', ') : 'N/A'}</p>
      <a href="${data.link}" target="_blank">View Details</a>
    `;

    hackathonsContainer.appendChild(card);
  });
}).catch(error => {
  console.error("Error fetching hackathons:", error);
});
