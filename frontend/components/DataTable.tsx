import type { ReactNode } from "react";

export function DataTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-silver bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-iron text-white">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 text-left font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-silver">
          {rows.map((row, i) => (
            <tr key={i} className="odd:bg-white even:bg-smoke hover:bg-lime/10">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 text-iron">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="px-4 py-6 text-center text-sm text-olive">Belum ada data.</p>
      )}
    </div>
  );
}
