// ADD EXPENSE MODAL
const addModal = document.getElementById('addExpenseModal');
const openAddBtn = document.getElementById('openAddExpenseModal');
const closeAddBtn = document.getElementById('closeAddModal');

openAddBtn.addEventListener('click', () => {
    addModal.style.display = 'flex';
});

closeAddBtn.addEventListener('click', () => {
    addModal.style.display = 'none';
});

// EDIT EXPENSE MODAL
const editModal = document.getElementById('editExpenseModal');
const closeEditBtn = document.getElementById('closeEditModal');
const editButtons = document.querySelectorAll('.edit-expense-btn');

editButtons.forEach(button => {
    button.addEventListener('click', () => {

        const expenseId = button.dataset.id;

        document.getElementById('editAmount').value = button.dataset.amount;
        document.getElementById('editCategory').value = button.dataset.category;
        document.getElementById('editDate').value = button.dataset.date;
        document.getElementById('editDescription').value = button.dataset.description;

        document.getElementById('editExpenseForm').action = `/shipments/${expenseId}/edit`;

        editModal.style.display = 'flex';
    });
});

closeEditBtn.addEventListener('click', () => {
    editModal.style.display = 'none';
});

// DELETE EXPENSE
document.querySelectorAll('.delete-expense-btn').forEach(button => {
    button.addEventListener('click', () => {
        if (!confirm('Delete this transaction? This cannot be undone.')) return;

        const expenseId = button.dataset.id;
        fetch(`/shipments/${expenseId}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.ok) location.reload();
            });
    });
});

// CLOSE WHEN CLICKING OUTSIDE
window.addEventListener('click', (e) => {
    if (e.target === addModal) {
        addModal.style.display = 'none';
    }

    if (e.target === editModal) {
        editModal.style.display = 'none';
    }
});