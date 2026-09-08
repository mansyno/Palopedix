/**
 * Utility to trigger client-side download of in-memory data as a JSON file.
 * Uses native browser Blob and URL.createObjectURL APIs with zero external dependencies.
 *
 * @param {any} data - The data object or array to export.
 * @param {string} filename - Target filename (e.g. 'base_optimizer_result.json').
 */
export function exportToJson(data, filename = 'export.json') {
  if (data === undefined || data === null) {
    console.warn('exportToJson: No data provided for export.');
    return;
  }

  try {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.json') ? filename : `${filename}.json`;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up allocated blob URL
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1000);
  } catch (err) {
    console.error('Failed to export JSON:', err);
  }
}
