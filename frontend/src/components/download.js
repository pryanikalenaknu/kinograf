/** Зберігає файл за адресою або з Blob через тимчасове посилання. */
export function saveFile(source, filename) {
  const href = source instanceof Blob ? URL.createObjectURL(source) : source;
  const link = document.createElement('a');
  link.href = href;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  if (source instanceof Blob) {
    setTimeout(() => URL.revokeObjectURL(href), 60_000);
  }
}
