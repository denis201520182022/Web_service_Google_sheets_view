let allUsers = [];
let editingUserId = null;

async function openUserManagement() {
    renderUserModal();
    await loadUsers();
}

function closeUserModal() {
    document.getElementById('user-modal-container').innerHTML = '';
    editingUserId = null;
}

// Загрузка списка пользователей
async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/api/admin/users`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            allUsers = await response.json();
            renderUserList();
        }
    } catch (e) {
        console.error("Ошибка загрузки пользователей", e);
    }
}

// Отрисовка основной модалки
function renderUserModal() {
    const container = document.getElementById('user-modal-container');
    container.innerHTML = `
        <div class="modal-overlay">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Управление пользователями</h2>
                    <button class="tool-btn" onclick="closeUserModal()">
                        <span class="material-icons">close</span>
                    </button>
                </div>
                
                <div id="user-form-container">
                    <button class="btn-add" onclick="showUserForm()">+ Добавить пользователя</button>
                </div>

                <table class="user-table">
                    <thead>
                        <tr>
                            <th>Имя</th>
                            <th>Логин</th>
                            <th>Роль</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody id="user-table-body">
                        <!-- Сюда попадут пользователи -->
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Форма (и для создания, и для редактирования)
function showUserForm(user = null) {
    editingUserId = user ? user.id : null;
    const formContainer = document.getElementById('user-form-container');
    
    formContainer.innerHTML = `
        <div class="user-form">
            <div class="form-group">
                <label>Имя</label>
                <input type="text" id="u-first-name" value="${user?.first_name || ''}">
            </div>
            <div class="form-group">
                <label>Фамилия</label>
                <input type="text" id="u-last-name" value="${user?.last_name || ''}">
            </div>
            <div class="form-group">
                <label>Логин *</label>
                <input type="text" id="u-username" value="${user?.username || ''}">
            </div>
            <div class="form-group">
                <label>Пароль ${user ? '(оставьте пустым, чтобы не менять)' : '*'}</label>
                <input type="password" id="u-password">
            </div>
            <div class="form-group full-width">
                <label style="display: flex; align-items: center; gap: 8px; cursor:pointer;">
                    <input type="checkbox" id="u-admin" ${user?.is_admin ? 'checked' : ''}>
                    Права администратора
                </label>
            </div>
            <div class="action-btns full-width">
                <button class="btn-save" onclick="saveUser()">${user ? 'Обновить' : 'Создать'}</button>
                <button class="btn-cancel" onclick="renderUserModal(); renderUserList();">Отмена</button>
            </div>
        </div>
    `;
}

function renderUserList() {
    const tbody = document.getElementById('user-table-body');
    tbody.innerHTML = allUsers.map(u => `
        <tr>
            <td>${u.first_name || ''} ${u.last_name || ''}</td>
            <td><strong>${u.username}</strong></td>
            <td>${u.is_admin ? '<span style="color:#667eea">Админ</span>' : 'Пользователь'}</td>
            <td class="action-btns">
                <button title="Редактировать" class="btn-edit" onclick="editUser(${u.id})">
                    <span class="material-icons">edit</span>
                </button>
                <button title="Удалить" class="btn-delete" onclick="confirmDelete(${u.id})">
                    <span class="material-icons">delete</span>
                </button>
            </td>
        </tr>
    `).join('');
}

async function saveUser() {
    const data = {
        username: document.getElementById('u-username').value,
        first_name: document.getElementById('u-first-name').value,
        last_name: document.getElementById('u-last-name').value,
        is_admin: document.getElementById('u-admin').checked,
        password: document.getElementById('u-password').value || null
    };

    const method = editingUserId ? 'PUT' : 'POST';
    const url = editingUserId ? `${API_URL}/api/admin/users/${editingUserId}` : `${API_URL}/api/admin/users`;

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Готово!');
            closeUserModal();
            openUserManagement(); // Перезагружаем список
        } else {
            const err = await response.json();
            alert('Ошибка: ' + (err.detail || 'не удалось сохранить'));
        }
    } catch (e) { console.error(e); }
}

function editUser(id) {
    const user = allUsers.find(u => u.id === id);
    if (user) showUserForm(user);
}

async function confirmDelete(id) {
    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) return;
    
    try {
        const response = await fetch(`${API_URL}/api/admin/users/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            loadUsers();
        }
    } catch (e) { console.error(e); }
}