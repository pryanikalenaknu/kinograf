/**
 * Копіює текст у буфер обміну.
 *
 * Clipboard API доступний лише на захищених адресах (HTTPS або localhost); якщо застосунок
 * відкрито за IP-адресою в локальній мережі, текст копіюється через тимчасове поле.
 *
 * @param {string} text текст для копіювання
 * @returns {Promise<boolean>} чи вдалося скопіювати
 */
export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return copyWithSelection(text);
    }
  }
  return copyWithSelection(text);
}

function copyWithSelection(text) {
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.style.position = 'fixed';
  field.style.opacity = '0';
  document.body.append(field);
  field.select();
  try {
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    field.remove();
  }
}
