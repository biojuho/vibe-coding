export const inputStyle={
  width:"100%",
  padding:"14px 16px",
  border:"1.5px solid var(--color-border)",
  borderRadius:"var(--radius-md)",
  fontSize:"14px",
  background:"var(--color-bg-card)",
  outline:"none",
  fontFamily:"var(--font-sans)",
  boxSizing:"border-box",
  transition:"all var(--transition-fast)"
};

export const labelStyle={
  fontSize:"12px",
  fontWeight:600,
  color:"var(--color-primary-light)",
  marginBottom:"6px",
  display:"block",
  fontFamily:"var(--font-sans)"
};

export const btnPrimary={
  background:"linear-gradient(135deg,var(--color-primary-light),var(--color-primary))",
  color:"white",
  border:"none",
  borderRadius:"var(--radius-md)",
  padding:"14px 24px",
  fontSize:"15px",
  fontWeight:700,
  cursor:"pointer",
  fontFamily:"var(--font-sans)",
  width:"100%",
  boxShadow:"0 4px 16px rgba(62,47,28,0.3)",
  transition:"all var(--transition-fast)"
};

export const btnSecondary={
  background:"var(--color-border)",
  color:"var(--color-primary)",
  border:"none",
  borderRadius:"var(--radius-md)",
  padding:"14px 24px",
  fontSize:"15px",
  fontWeight:600,
  cursor:"pointer",
  fontFamily:"var(--font-sans)",
  width:"100%",
  transition:"all var(--transition-fast)"
};

export const btnDanger={
  background:"var(--color-danger-light)",
  color:"var(--color-danger)",
  border:"1.5px solid #FFCDD2",
  borderRadius:"var(--radius-md)",
  padding:"12px 20px",
  fontSize:"14px",
  fontWeight:600,
  cursor:"pointer",
  fontFamily:"var(--font-sans)",
  transition:"all var(--transition-fast)"
};

export const BackIcon=()=><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>;
export const PlusIcon=()=><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>;
export const EditIcon=()=><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>;
export const TrashIcon=()=><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>;
export const HeartIcon=()=><svg width="16" height="16" viewBox="0 0 24 24" fill="#E91E63" stroke="#E91E63" strokeWidth="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>;
