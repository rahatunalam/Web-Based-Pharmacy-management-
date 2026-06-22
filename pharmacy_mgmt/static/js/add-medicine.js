const form = document.getElementById('medicineForm');
const tableBody = document.getElementById('medicineTableBody');

const currency = n => '৳' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function attachDeleteHandler(button) {
  button.addEventListener('click', () => {
    const row = button.closest('tr');
    row.remove();
  });
}

// Wire up the delete button on the pre-existing sample row
document.querySelectorAll('.row-delete').forEach(attachDeleteHandler);

form.addEventListener('submit', e => {
  e.preventDefault();

  const name = document.getElementById('productName').value.trim();
  const type = document.getElementById('productType').value;
  const quantity = parseFloat(document.getElementById('quantity').value);
  const price = parseFloat(document.getElementById('price').value);

  if (!name || !type || !quantity || !price) return;

  const total = quantity * price;

  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${name}</td>
    <td><span class="pill">${type}</span></td>
    <td class="num">${quantity}</td>
    <td class="num">${currency(price)}</td>
    <td class="num">${currency(total)}</td>
    <td>
      <button class="row-delete" aria-label="Remove row">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/></svg>
      </button>
    </td>
  `;

  tableBody.appendChild(row);
  attachDeleteHandler(row.querySelector('.row-delete'));

  form.reset();
  document.getElementById('productName').focus();
});
