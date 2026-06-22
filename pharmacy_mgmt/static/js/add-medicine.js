const form = document.getElementById('medicineForm');
const tableBody = document.getElementById('medicineTableBody');

// NEW — tracks how many rows have been added (never resets, even after deletes)
let rowCount = 0;

const currency = n => '৳' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function attachDeleteHandler(button, index) {  // NEW — added index parameter
  button.addEventListener('click', () => {
    const row = button.closest('tr');
    row.remove();

    // NEW — when a row is deleted, also remove its hidden inputs from dbForm
    const hiddenDiv = document.getElementById('hiddenInputs');
    hiddenDiv.querySelectorAll(`[data-row="${index}"]`).forEach(input => input.remove());

    // NEW — update the count Django will read
    updateTotalCount();
  });
}

// NEW — counts visible rows and updates the hidden total_count input
function updateTotalCount() {
  const visibleRows = tableBody.querySelectorAll('tr').length;
  let countInput = document.getElementById('totalCount');
  if (!countInput) {
    countInput = document.createElement('input');
    countInput.type = 'hidden';
    countInput.name = 'total_count';
    countInput.id = 'totalCount';
    document.getElementById('hiddenInputs').appendChild(countInput);
  }
  countInput.value = visibleRows;
}

document.querySelectorAll('.row-delete').forEach(btn => attachDeleteHandler(btn, -1));

form.addEventListener('submit', e => {
  e.preventDefault();

  const name = document.getElementById('productName').value.trim();
  const type = document.getElementById('productType').value;
  const quantity = parseFloat(document.getElementById('quantity').value);
  const price = parseFloat(document.getElementById('price').value);

  if (!name || !type || !quantity || !price) return;

  const total = quantity * price;

  // NEW — capture current index before incrementing
  const index = rowCount;

  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${name}</td>
    <td><span class="pill">${type}</span></td>
    <td class="num">${quantity}</td>
    <td class="num">${currency(price)}</td>
    <td class="num">${currency(total)}</td>
    <td>
      <button type="button" class="row-delete" aria-label="Remove row">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/></svg>
      </button>
    </td>
  `;

  tableBody.appendChild(row);
  attachDeleteHandler(row.querySelector('.row-delete'), index);  // NEW — pass index

  // NEW — inject hidden inputs so Django can read this row
  const hiddenDiv = document.getElementById('hiddenInputs');
  hiddenDiv.innerHTML += `
    <input type="hidden" name="medicine_${index}_name"     value="${name}"     data-row="${index}">
    <input type="hidden" name="medicine_${index}_type"     value="${type}"     data-row="${index}">
    <input type="hidden" name="medicine_${index}_quantity" value="${quantity}" data-row="${index}">
    <input type="hidden" name="medicine_${index}_price"    value="${price}"    data-row="${index}">
  `;

  // NEW — increment the counter and update total_count
  rowCount++;
  updateTotalCount();

  form.reset();
  document.getElementById('productName').focus();
});