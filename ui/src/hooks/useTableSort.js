import { useState, useMemo } from 'react';

/**
 * Reusable table sorting hook for list data.
 * @param {Array} data - Input array of objects to sort
 * @param {string} initialCol - Default sort column key
 * @param {boolean} initialDesc - Default sort direction (true = descending)
 */
export function useTableSort(data, initialCol = '', initialDesc = false) {
  const [sortCol, setSortCol] = useState(initialCol);
  const [sortDesc, setSortDesc] = useState(initialDesc);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(prev => !prev);
    } else {
      setSortCol(col);
      setSortDesc(false);
    }
  };

  const sortedData = useMemo(() => {
    const list = Array.isArray(data) ? [...data] : [];
    if (!sortCol) return list;

    return list.sort((a, b) => {
      let valA = a[sortCol];
      let valB = b[sortCol];

      if (valA === undefined || valA === null) valA = '';
      if (valB === undefined || valB === null) valB = '';

      if (typeof valA === 'string' && typeof valB === 'string') {
        const cmp = valA.localeCompare(valB);
        return sortDesc ? -cmp : cmp;
      }

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDesc ? valB - valA : valA - valB;
      }

      if (valA < valB) return sortDesc ? 1 : -1;
      if (valA > valB) return sortDesc ? -1 : 1;
      return 0;
    });
  }, [data, sortCol, sortDesc]);

  return {
    sortedData,
    sortCol,
    sortDesc,
    handleSort,
    setSortCol,
    setSortDesc,
  };
}
