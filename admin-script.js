let localAdminArray = []; // מערך מקומי לצורך תצוגה ומיונים

// פונקציה שמושכת את רשימת המשתמשים העדכנית ממערך הפייתון של השרת
function fetchUsersFromServer() {
    fetch('http://localhost:5000/api/users')
        .then(response => response.json())
        .then(data => {
            localAdminArray = data;
            renderTable();
        })
        .catch(error => console.error('Error fetching users:', error));
}

// בניית הטבלה החזותית על המסך
function renderTable() {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    localAdminArray.forEach((user) => {
        const row = document.createElement('tr');
        const encryptedDisplay = '••••••••';
        const badgeClass = user.isAdmin ? 'status-true' : 'status-false';

        row.innerHTML = `
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td class="encrypted-pass">${encryptedDisplay}</td>
            <td><span class="status-badge ${badgeClass}">${user.isAdmin}</span></td>
            <td>${user.lastLogin}</td>
            <td>
                <button class="delete-btn" onclick="deleteUser('${user.username}')">✖</button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// פונקציית מחיקה - שולחת הודעה לפייתון למחוק את המשתמש מהמערך המרכזי
function deleteUser(username) {
    const isConfirmed = confirm(`האם אתה בטוח שברצונך למחוק לצמיתות את המשתמש "${username}"?`);
    if (!isConfirmed) return;

    fetch(`http://localhost:5000/api/delete/${username}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`המשתמש "${username}" נמחק בהצלחה ולא יוכל להיכנס יותר לאתר.`);
                fetchUsersFromServer(); // טעינת הטבלה מחדש
            }
        });
}

// כפתורי המיון
document.getElementById('sortByUserBtn').addEventListener('click', function() {
    localAdminArray.sort((a, b) => a.username.localeCompare(b.username));
    renderTable();
});

document.getElementById('sortByDateBtn').addEventListener('click', function() {
    localAdminArray.sort((a, b) => b.lastLogin.localeCompare(a.lastLogin));
    renderTable();
});

// עדכון הטבלה כל 3 שניות אוטומטית
fetchUsersFromServer();
setInterval(fetchUsersFromServer, 3000);
