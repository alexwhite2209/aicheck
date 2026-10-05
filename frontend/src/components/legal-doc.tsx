export const OPERATOR = {
  name: process.env.NEXT_PUBLIC_OPERATOR_NAME || "[наименование оператора]",
  inn: process.env.NEXT_PUBLIC_OPERATOR_INN || "[ИНН]",
  ogrn: process.env.NEXT_PUBLIC_OPERATOR_OGRN || "[ОГРН / ОГРНИП]",
  address: process.env.NEXT_PUBLIC_OPERATOR_ADDRESS || "[адрес места нахождения]",
  email: process.env.NEXT_PUBLIC_OPERATOR_EMAIL || "[email для обращений]",
};

export function LegalDoc({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-[30px] font-semibold tracking-tight">{title}</h1>
      <div className="mt-2 text-[13px] text-dim">Редакция от {updated}</div>
      <div className="prose-legal mt-8">{children}</div>
    </div>
  );
}

export function OperatorBlock() {
  return (
    <p>
      Оператор: {OPERATOR.name}, ИНН {OPERATOR.inn}, {OPERATOR.ogrn}, адрес: {OPERATOR.address}, email: {OPERATOR.email}.
    </p>
  );
}
