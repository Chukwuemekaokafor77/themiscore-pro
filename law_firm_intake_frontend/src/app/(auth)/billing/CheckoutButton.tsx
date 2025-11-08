"use client";

export default function CheckoutButton({ invoiceId }: { invoiceId: number }) {
  const onClick = async () => {
    try {
      const res = await fetch('/api/staff/payments/stripe/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_id: invoiceId }),
      });
      if (res.status === 501) {
        alert('Stripe not configured');
        return;
      }
      if (!res.ok) {
        alert(`Checkout failed (${res.status})`);
        return;
      }
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert('No checkout URL returned');
      }
    } catch (err) {
      alert('Request failed');
    }
  };
  return (
    <button onClick={onClick} className="px-3 py-1 bg-primary text-primary-foreground hover:opacity-90 rounded-md text-xs">
      Pay
    </button>
  );
}
