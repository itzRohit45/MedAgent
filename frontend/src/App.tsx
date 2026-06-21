import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Toaster, toast as hotToast } from 'react-hot-toast';
import {
  Activity, Calendar, Pill, FilePlus, ShieldAlert,
  Bell, FileBarChart, Plus, Upload, Trash2, CheckCircle2, XCircle, AlertCircle, Clock,
  MessageSquare, BarChart3, Package, Thermometer, BookOpen, Zap, Users, Send, Bot, User, Info, ChevronDown, ChevronUp
} from 'lucide-react';
import './index.css';

interface Patient {
  id: number;
  name: string;
}

export default function App() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [activePatient, setActivePatient] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<string>('risk_dashboard');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ meds: 0, todayDoses: 0, adherence: 0, interactions: 0 });
  const [showAddPatient, setShowAddPatient] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (activePatient) {
      refreshStats();
    }
  }, [activePatient, activeTab]);

  const fetchInitialData = async () => {
    try {
      const res = await axios.get('/api/patients');
      setPatients(res.data);
      if (res.data.length > 0) {
        setActivePatient(res.data[0].id);
      } else {
        setActivePatient(0);
      }
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch patients", err);
      setLoading(false);
    }
  };

  const deletePatient = async () => {
    if (!window.confirm("Are you sure you want to permanently delete this patient and all their data?")) return;
    try {
      await axios.delete(`/api/patients/${activePatient}`);
      hotToast.success("Patient deleted");
      fetchInitialData();
    } catch (err) {
      hotToast.error("Failed to delete patient");
    }
  };

  const refreshStats = async () => {
    try {
      const [meds, sched, adh] = await Promise.all([
        axios.get(`/api/medications/${activePatient}`),
        axios.get(`/api/schedule/${activePatient}`),
        axios.get(`/api/adherence/${activePatient}`)
      ]);
      setStats({
        meds: meds.data.length,
        todayDoses: sched.data.length,
        adherence: adh.data.adherence_pct,
        interactions: 0
      });
    } catch (err) {
      console.error("Stats refresh failed", err);
    }
  };

  if (loading) return <div className="full-screen-loader"><Activity className="loader-icon" /></div>;

  const tabTitle: Record<string, string> = {
    risk_dashboard: 'Patient Risk Dashboard',
    dashboard: 'Daily Schedule',
    medications: 'Medications List',
    intake: 'Add Prescription',
    interactions: 'Drug Interactions',
    analytics: 'Adherence Analytics',
    side_effects: 'Side Effect Monitor',
    chat: 'AI Assistant',
    reminders: 'Automation & Alerts',
    reports: 'Caregiver Reports',
  };

  return (
    <div className="layout">
      <Toaster position="bottom-right" />
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <Activity className="brand-icon" />
          <span className="brand-text">MedAgent</span>
        </div>

        <div className="patient-section">
          <label className="section-label">Current Patient</label>
          <div className="patient-controls">
            <select
              className="patient-select"
              value={activePatient}
              onChange={(e) => setActivePatient(Number(e.target.value))}
            >
              {patients.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button className="icon-btn" onClick={() => setShowAddPatient(true)} title="Add Patient">
              <Plus size={16} />
            </button>
            <button className="icon-btn danger" onClick={deletePatient} title="Delete Patient" disabled={patients.length === 0}>
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        <nav className="nav-menu">
          <label className="section-label">Navigation</label>
          <button className={`nav-item ${activeTab === 'risk_dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('risk_dashboard')}>
            <Users size={18} /> Risk Dashboard
          </button>
          <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <Calendar size={18} /> Daily Schedule
          </button>
          <button className={`nav-item ${activeTab === 'medications' ? 'active' : ''}`} onClick={() => setActiveTab('medications')}>
            <Pill size={18} /> Medications List
          </button>
          <button className={`nav-item ${activeTab === 'intake' ? 'active' : ''}`} onClick={() => setActiveTab('intake')}>
            <FilePlus size={18} /> Add Prescription
          </button>
          <button className={`nav-item ${activeTab === 'interactions' ? 'active' : ''}`} onClick={() => setActiveTab('interactions')}>
            <ShieldAlert size={18} /> Drug Interactions
          </button>
          <button className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <BarChart3 size={18} /> Analytics
          </button>
          <button className={`nav-item ${activeTab === 'side_effects' ? 'active' : ''}`} onClick={() => setActiveTab('side_effects')}>
            <Thermometer size={18} /> Side Effects
          </button>
          <button className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            <MessageSquare size={18} /> AI Chat
          </button>
          <button className={`nav-item ${activeTab === 'reminders' ? 'active' : ''}`} onClick={() => setActiveTab('reminders')}>
            <Bell size={18} /> Automation & Alerts
          </button>
          <button className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
            <FileBarChart size={18} /> Caregiver Reports
          </button>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="topbar">
          <h2 className="page-title">{tabTitle[activeTab] || activeTab}</h2>
          <div className="quick-metrics">
            <span className="metric-badge">Adherence: <strong style={{ color: stats.adherence >= 90 ? 'var(--color-success)' : 'var(--color-warning)' }}>{stats.adherence}%</strong></span>
            {stats.interactions > 0 && <span className="metric-badge danger"><AlertCircle size={14} /> {stats.interactions} Interactions</span>}
          </div>
        </header>

        <div className="content-area">
          {activeTab === 'risk_dashboard' && <RiskDashboardTab onSelectPatient={(id) => { setActivePatient(id); setActiveTab('dashboard'); }} />}
          {activeTab === 'dashboard' && <ScheduleTab patientId={activePatient} />}
          {activeTab === 'medications' && <MedicationsTab patientId={activePatient} />}
          {activeTab === 'intake' && <IntakeTab patientId={activePatient} onComplete={refreshStats} />}
          {activeTab === 'interactions' && <InteractionsTab patientId={activePatient} />}
          {activeTab === 'analytics' && <AnalyticsTab patientId={activePatient} />}
          {activeTab === 'side_effects' && <SideEffectsTab patientId={activePatient} />}
          {activeTab === 'chat' && <ChatTab patientId={activePatient} />}
          {activeTab === 'reminders' && <RemindersTab patientId={activePatient} />}
          {activeTab === 'reports' && <ReportsTab patientId={activePatient} />}
        </div>
      </main>

      {/* Add Patient Modal */}
      {showAddPatient && (
        <AddPatientModal
          onClose={() => setShowAddPatient(false)}
          onSuccess={(id) => {
            fetchInitialData();
            setActivePatient(id);
            setShowAddPatient(false);
          }}
        />
      )}
    </div>
  );
}

// ── Feature 7: Risk Dashboard ──────────────────────────────────────────────

function RiskDashboardTab({ onSelectPatient }: { onSelectPatient: (id: number) => void }) {
  const [risks, setRisks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchRisks(); }, []);

  const fetchRisks = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/dashboard/overview');
      setRisks(res.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="loader"><Activity className="loader-icon-small" /></div>;

  return (
    <div className="panel">
      <div className="panel-header-actions">
        <p className="panel-desc">All patients ranked by risk score. Higher score = higher risk.</p>
        <button className="btn outline small" onClick={fetchRisks}>Refresh</button>
      </div>
      {risks.length === 0 ? (
        <div className="empty-state"><Users size={48} /><p>No patients found. Add a patient to get started.</p></div>
      ) : (
        <div className="risk-grid">
          {risks.map((r: any) => (
            <div key={r.patient_id} className={`risk-card risk-${r.risk_level}`} onClick={() => onSelectPatient(r.patient_id)}>
              <div className="risk-card-header">
                <h4>{r.patient_name}</h4>
                <div className={`risk-score-badge ${r.risk_level}`}>{r.risk_score}</div>
              </div>
              <div className="risk-card-body">
                <div className="risk-metric">
                  <span className="risk-metric-label">Adherence</span>
                  <span className="risk-metric-value">{r.adherence_pct}%</span>
                </div>
                <div className="risk-metric">
                  <span className="risk-metric-label">Active Meds</span>
                  <span className="risk-metric-value">{r.active_meds}</span>
                </div>
                <div className="risk-metric">
                  <span className="risk-metric-label">Critical</span>
                  <span className="risk-metric-value">{r.critical_meds}</span>
                </div>
                <div className="risk-metric">
                  <span className="risk-metric-label">Missed (24h)</span>
                  <span className="risk-metric-value">{r.missed_24h}</span>
                </div>
              </div>
              <div className={`risk-level-tag ${r.risk_level}`}>{r.risk_level.toUpperCase()} RISK</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Existing Components ────────────────────────────────────────────────────

function ScheduleTab({ patientId }: { patientId: number }) {
  const [schedule, setSchedule] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchSchedule(); }, [patientId]);

  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/schedule/${patientId}`);
      setSchedule(res.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const markDose = async (id: number, action: string) => {
    await axios.post(`/api/schedule/${id}/confirm`, { action });
    fetchSchedule();
  };

  if (loading) return <div className="loader"><Activity className="loader-icon-small" /></div>;

  return (
    <div className="panel">
      {schedule.length === 0 ? (
        <div className="empty-state">
          <Calendar size={48} />
          <p>No doses scheduled for today.</p>
        </div>
      ) : (
        <div className="data-list">
          {schedule.map((dose: any) => (
            <div key={dose.id} className="data-row">
              <div className="row-main">
                <div className="time-badge">{new Date(dose.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                <div>
                  <h4 className="row-title">{dose.drug_name} {dose.is_critical ? <span className="tag critical">Critical</span> : ''}</h4>
                  <p className="row-subtitle">Dose: {dose.dose}</p>
                </div>
              </div>
              <div className="row-actions">
                {dose.status === 'pending' ? (
                  <>
                    <button className="btn outline" onClick={() => markDose(dose.id, 'skipped')}><XCircle size={16} /> Skip</button>
                    <button className="btn success" onClick={() => markDose(dose.id, 'taken')}><CheckCircle2 size={16} /> Take</button>
                  </>
                ) : (
                  <span className={`status-text ${dose.status}`}>{dose.status.toUpperCase()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MedicationsTab({ patientId }: { patientId: number }) {
  const [meds, setMeds] = useState<any[]>([]);
  const [editingMed, setEditingMed] = useState<number | null>(null);
  const [editTimes, setEditTimes] = useState<string>('');
  const [refills, setRefills] = useState<any[]>([]);
  const [eduData, setEduData] = useState<any>(null);
  const [eduLoading, setEduLoading] = useState<number | null>(null);
  const [showEduModal, setShowEduModal] = useState(false);

  useEffect(() => { fetchMeds(); fetchRefills(); }, [patientId]);

  const fetchMeds = async () => {
    const res = await axios.get(`/api/medications/${patientId}`);
    setMeds(res.data);
  };

  const fetchRefills = async () => {
    try {
      const res = await axios.get(`/api/refills/${patientId}`);
      setRefills(res.data);
    } catch (e) { console.error(e); }
  };

  const deleteMed = async (id: number) => {
    await axios.delete(`/api/medications/${id}`);
    fetchMeds();
  };

  const saveTimes = async (id: number) => {
    const timesArray = editTimes.split(',').map(t => {
      let trimmed = t.trim();
      if (trimmed.match(/^\d:\d\d$/)) {
        trimmed = '0' + trimmed;
      }
      return trimmed;
    }).filter(t => t.match(/^([01]\d|2[0-3]):[0-5]\d$/));
    if (timesArray.length === 0) {
      hotToast.error("Please enter valid times (e.g. 09:00, 14:00)");
      return;
    }
    try {
      await axios.put(`/api/medications/${id}/times`, {
        patient_id: patientId,
        times: timesArray
      });
      setEditingMed(null);
      fetchMeds();
      hotToast.success("Schedule updated!");
    } catch (e) {
      hotToast.error("Failed to update schedule");
    }
  };

  const setPills = async (medId: number) => {
    const count = prompt("Enter current pill count:");
    if (count === null || isNaN(Number(count))) return;
    await axios.put(`/api/medications/${medId}/pills`, { count: parseInt(count) });
    fetchRefills();
    hotToast.success("Pill count updated!");
  };

  const showEducation = async (medId: number) => {
    setEduLoading(medId);
    try {
      const res = await axios.get(`/api/education/${medId}`);
      setEduData(res.data);
      setShowEduModal(true);
    } catch (e) {
      hotToast.error("Failed to load drug info");
    }
    setEduLoading(null);
  };

  const getRefillInfo = (medId: number) => refills.find(r => r.medication_id === medId);

  return (
    <>
      <div className="panel">
        {meds.length === 0 ? (
          <div className="empty-state">
            <Pill size={48} />
            <p>No active medications found.</p>
          </div>
        ) : (
          <div className="data-list">
            {meds.map((med: any) => {
              const refillInfo = getRefillInfo(med.id);
              return (
                <React.Fragment key={med.id}>
                  <div className="data-row">
                    <div className="row-main">
                      <div>
                        <h4 className="row-title">{med.drug_name} {med.is_critical ? <span className="tag critical">Critical</span> : ''}</h4>
                        <p className="row-subtitle">Generic: {med.generic_name || 'N/A'}</p>
                      </div>
                    </div>
                    <div className="row-meta">
                      <div className="meta-block">
                        <span className="meta-label">Dose</span>
                        <span className="meta-value">{med.dose}</span>
                      </div>
                      <div className="meta-block">
                        <span className="meta-label">Frequency</span>
                        <span className="meta-value">
                          {med.frequency}
                          {(() => {
                            let timesList = med.times;
                            if (typeof timesList === 'string') {
                              try { timesList = JSON.parse(timesList); } catch { timesList = []; }
                            }

                            if (Array.isArray(timesList) && timesList.length > 0 && timesList[0] !== "") {
                              return (
                                <span className="times-list">
                                  {' '}
                                  ({timesList.join(', ')})
                                </span>
                              );
                            }
                            return null;
                          })()}
                        </span>
                      </div>
                      {refillInfo && refillInfo.pills_remaining !== null && (
                        <div className="meta-block">
                          <span className="meta-label">Pills Left</span>
                          <span className={`meta-value ${refillInfo.days_remaining !== null && refillInfo.days_remaining <= 3 ? 'text-danger' : refillInfo.days_remaining !== null && refillInfo.days_remaining <= 7 ? 'text-warning' : ''}`}>
                            {refillInfo.pills_remaining} ({refillInfo.days_remaining}d)
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="row-actions">
                      <button className="icon-btn has-tooltip" style={{ color: 'var(--color-primary)' }} onClick={() => showEducation(med.id)} data-tooltip="Drug Info">
                        {eduLoading === med.id ? <Activity size={18} className="loader-icon-small" /> : <BookOpen size={18} />}
                      </button>
                      <button className="icon-btn has-tooltip" style={{ color: 'var(--color-success)' }} onClick={() => setPills(med.id)} data-tooltip="Set Pill Count">
                        <Package size={18} />
                      </button>
                      <button
                        className="icon-btn has-tooltip"
                        style={{ color: 'var(--color-primary)' }}
                        onClick={() => {
                          setEditingMed(editingMed === med.id ? null : med.id);
                          let t = med.times;
                          if (typeof t === 'string') { try { t = JSON.parse(t); } catch { t = []; } }
                          setEditTimes(Array.isArray(t) ? t.join(', ') : '');
                        }}
                        data-tooltip="Edit Times"
                      >
                        <Clock size={18} />
                      </button>
                      <button className="icon-btn danger has-tooltip" onClick={() => deleteMed(med.id)} data-tooltip="Remove Medication">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                  {editingMed === med.id && (
                    <div className="edit-times-container" style={{ padding: '10px 15px', backgroundColor: 'var(--bg-secondary)', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <Clock size={16} style={{ color: 'var(--text-secondary)' }} />
                      <input
                        type="text"
                        value={editTimes}
                        onChange={(e) => setEditTimes(e.target.value)}
                        className="input-field"
                        style={{ flex: 1, padding: '8px', fontSize: '0.9rem' }}
                        placeholder="e.g. 09:00, 14:00, 21:00"
                      />
                      <button className="btn success" onClick={() => saveTimes(med.id)} style={{ padding: '6px 12px' }}>Save</button>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        )}
      </div>

      {/* Education Modal */}
      {showEduModal && eduData && (
        <div className="modal-overlay" onClick={() => setShowEduModal(false)}>
          <div className="modal-content edu-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><BookOpen size={20} /> {eduData.drug_name}</h3>
              <button className="icon-btn" onClick={() => setShowEduModal(false)}><XCircle size={20} /></button>
            </div>
            <div className="edu-content">
              <div className="edu-section">
                <h4>💊 What does this medicine do?</h4>
                <p>{eduData.purpose}</p>
              </div>
              <div className="edu-section">
                <h4>📋 How to take it</h4>
                <p>{eduData.how_to_take}</p>
              </div>
              {eduData.common_side_effects?.length > 0 && (
                <div className="edu-section">
                  <h4>⚠️ Common side effects</h4>
                  <ul>{eduData.common_side_effects.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
                </div>
              )}
              {eduData.important_warnings?.length > 0 && (
                <div className="edu-section warning">
                  <h4>🚨 Important warnings</h4>
                  <ul>{eduData.important_warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul>
                </div>
              )}
              {eduData.tips?.length > 0 && (
                <div className="edu-section tip">
                  <h4>💡 Helpful tips</h4>
                  <ul>{eduData.tips.map((t: string, i: number) => <li key={i}>{t}</li>)}</ul>
                </div>
              )}
              {eduData.interactions_to_avoid && (
                <div className="edu-section">
                  <h4>🚫 Things to avoid</h4>
                  <p>{eduData.interactions_to_avoid}</p>
                </div>
              )}
              <p className="edu-disclaimer">{eduData.disclaimer}</p>
              <p className="edu-source">Source: {eduData.source}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function IntakeTab({ patientId, onComplete }: { patientId: number, onComplete: () => void }) {
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleTextParse = async () => {
    if (!text) return;
    setLoading(true);
    try {
      const res = await axios.post('/api/intake/text', { patient_id: patientId, text });
      setResult(res.data);
      onComplete();
      hotToast.success("Prescription processed successfully");
    } catch (e: any) {
      console.error(e);
      hotToast.error(e.response?.data?.detail || "Error processing text prescription");
    }
    setLoading(false);
  };

  const handleImageParse = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('patient_id', patientId.toString());
      formData.append('file', file);

      const res = await axios.post('/api/intake/image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(res.data);
      onComplete();
      hotToast.success("Prescription processed successfully");
    } catch (e: any) {
      console.error(e);
      hotToast.error(e.response?.data?.detail || "Error processing image prescription");
    }
    setLoading(false);
  };

  return (
    <div className="two-col-grid" style={{ alignItems: 'stretch' }}>
      <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
        <h3 className="panel-title">Text Input</h3>
        <p className="panel-desc">Paste prescription details manually for automated extraction.</p>
        <textarea
          className="form-textarea"
          style={{ flex: 1 }}
          placeholder="e.g. Amlodipine 5mg once daily in the morning"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn primary full-width" style={{ marginTop: 'auto' }} onClick={handleTextParse} disabled={loading || !text}>
          {loading ? 'Processing...' : 'Process Text'}
        </button>
      </div>

      <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
        <h3 className="panel-title">Image Upload</h3>
        <p className="panel-desc">Upload a picture of a physical prescription.</p>
        <div style={{ display: 'flex', gap: '1rem', flex: 1 }}>
          <div className="file-drop-zone" style={{ flex: 1, padding: '2rem 1rem' }} onClick={() => fileInputRef.current?.click()}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <Upload size={24} className="drop-icon" />
            <p style={{ fontSize: '0.9rem' }}>{file ? file.name : "Upload Image"}</p>
          </div>
          <div className="file-drop-zone" style={{ flex: 1, padding: '2rem 1rem' }} onClick={() => {
            const el = document.getElementById('cameraInput');
            if (el) el.click();
          }}>
            <input
              id="cameraInput"
              type="file"
              style={{ display: 'none' }}
              accept="image/*"
              capture="environment"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <Activity size={24} className="drop-icon" />
            <p style={{ fontSize: '0.9rem' }}>Take Photo</p>
          </div>
        </div>
        <button className="btn primary full-width" onClick={handleImageParse} disabled={loading || !file}>
          {loading ? 'Processing...' : 'Process Image'}
        </button>
      </div>

      {result && (
        <div className="panel col-span-2 result-panel">
          <h3 className="panel-title success">Extraction Complete</h3>
          <p className="panel-desc">Saved {result.saved?.length || 0} medications successfully.</p>
          <div className="data-list mt-4">
            {result.saved?.map((m: any, i: number) => (
              <div key={i} className="data-row compact">
                <strong>{m.drug}</strong> — {m.dose} ({m.frequency})
              </div>
            ))}
          </div>

          {result.needs_confirmation?.length > 0 && (
            <div className="mt-4" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '15px' }}>
              <h4 className="panel-title warning" style={{ color: 'var(--color-warning)', margin: 0 }}>Needs Clarification</h4>
              <p className="panel-desc" style={{ marginBottom: '10px' }}>The AI could not confidently read some details from the image.</p>
              <div className="data-list">
                {result.needs_confirmation.map((m: any, i: number) => (
                  <div key={i} className="data-row compact" style={{ borderLeft: '3px solid var(--color-warning)' }}>
                    <strong>{m.drug || m.generic_name || 'Unknown Drug'}</strong>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9em', marginTop: '5px' }}>
                      <strong>AI Question:</strong> {m.question || "Missing critical dose or frequency information."}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InteractionsTab({ patientId }: { patientId: number }) {
  const [flags, setFlags] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchFlags(); }, [patientId]);

  const fetchFlags = async () => {
    try {
      const res = await axios.get(`/api/interactions/${patientId}`);
      setFlags(res.data?.flags || res.data || []);
    } catch (e: any) {
      console.error(e);
      hotToast.error(e.response?.data?.detail || "Failed to load drug interactions.");
      setFlags([]);
    }
  };

  const recheck = async () => {
    setLoading(true);
    await fetchFlags();
    setLoading(false);
  };

  return (
    <div className="panel">
      <div className="panel-header-actions">
        <p className="panel-desc">Cross-references active medications against clinical safety databases.</p>
        <button className="btn outline small" onClick={recheck} disabled={loading}>
          {loading ? 'Analyzing...' : 'Run Safety Check'}
        </button>
      </div>

      {flags.length === 0 ? (
        <div className="empty-state">
          <CheckCircle2 size={48} className="text-success" />
          <p>No safety alerts or interactions detected.</p>
        </div>
      ) : (
        <div className="data-list mt-4">
          {flags.map((flag: any, i: number) => (
            <div key={i} className={`data-row alert-${flag.severity.toLowerCase()}`}>
              <div className="row-main">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={`tag ${flag.severity.toLowerCase()}`}>{flag.severity.toUpperCase()}</span>
                  <h4 className="row-title" style={{ margin: 0 }}>
                    {flag.drugs ? flag.drugs.join(' + ') : `${flag.drug1} + ${flag.drug2}`}
                  </h4>
                </div>
                <p className="row-subtitle mt-2">{flag.note || flag.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Feature 2: Analytics Tab ──────────────────────────────────────────────

function AnalyticsTab({ patientId }: { patientId: number }) {
  const [trend, setTrend] = useState<any[]>([]);
  const [breakdown, setBreakdown] = useState<any[]>([]);
  const [insights, setInsights] = useState<any>(null);
  const [optimization, setOptimization] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [insightLoading, setInsightLoading] = useState(false);
  const [optLoading, setOptLoading] = useState(false);

  useEffect(() => { fetchData(); }, [patientId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [t, b] = await Promise.all([
        axios.get(`/api/adherence/${patientId}/trend?days=14`),
        axios.get(`/api/adherence/${patientId}/breakdown?days=14`),
      ]);
      setTrend(t.data);
      setBreakdown(b.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const fetchInsights = async () => {
    setInsightLoading(true);
    try {
      const res = await axios.get(`/api/analytics/${patientId}`);
      setInsights(res.data);
    } catch (e) { hotToast.error("Failed to generate insights"); }
    setInsightLoading(false);
  };

  const fetchOptimization = async () => {
    setOptLoading(true);
    try {
      const res = await axios.get(`/api/optimize/${patientId}`);
      setOptimization(res.data);
    } catch (e) { hotToast.error("Failed to generate optimization suggestions"); }
    setOptLoading(false);
  };

  if (loading) return <div className="loader"><Activity className="loader-icon-small" /></div>;

  const maxTotal = Math.max(...trend.map(t => t.total), 1);

  return (
    <div className="analytics-layout">
      {/* Trend Chart */}
      <div className="panel">
        <h3 className="panel-title"><BarChart3 size={18} /> Adherence Trend (14 days)</h3>
        {trend.length === 0 ? (
          <div className="empty-state"><p>No dose data yet.</p></div>
        ) : (
          <div className="chart-container">
            {trend.map((day, i) => (
              <div key={i} className="chart-bar-group">
                <div className="chart-bar-stack" style={{ height: '120px' }}>
                  <div className="chart-bar taken" style={{ height: `${(day.taken / maxTotal) * 100}%` }} title={`Taken: ${day.taken}`}></div>
                  <div className="chart-bar missed" style={{ height: `${(day.missed / maxTotal) * 100}%` }} title={`Missed: ${day.missed}`}></div>
                  <div className="chart-bar skipped" style={{ height: `${(day.skipped / maxTotal) * 100}%` }} title={`Skipped: ${day.skipped}`}></div>
                </div>
                <span className="chart-label">{day.date.slice(5)}</span>
                <span className="chart-pct">{day.adherence_pct}%</span>
              </div>
            ))}
          </div>
        )}
        <div className="chart-legend">
          <span><span className="legend-dot taken"></span> Taken</span>
          <span><span className="legend-dot missed"></span> Missed</span>
          <span><span className="legend-dot skipped"></span> Skipped</span>
        </div>
      </div>

      {/* Per-Medication Breakdown */}
      <div className="panel">
        <h3 className="panel-title"><Pill size={18} /> Per-Medication Adherence</h3>
        {breakdown.length === 0 ? (
          <div className="empty-state"><p>No medication data yet.</p></div>
        ) : (
          <div className="data-list">
            {breakdown.map((med, i) => (
              <div key={i} className="data-row compact">
                <div className="row-main" style={{ flex: 1 }}>
                  <strong>{med.medication}</strong>
                  <div className="progress-bar-container">
                    <div className="progress-bar" style={{ width: `${med.adherence_pct}%`, backgroundColor: med.adherence_pct >= 90 ? 'var(--color-success)' : med.adherence_pct >= 70 ? 'var(--color-warning)' : 'var(--color-danger)' }}></div>
                  </div>
                </div>
                <span className="adherence-pct">{med.adherence_pct}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Insights */}
      <div className="panel">
        <div className="panel-header-actions">
          <h3 className="panel-title"><Zap size={18} /> AI Insights</h3>
          <button className="btn primary small" onClick={fetchInsights} disabled={insightLoading}>
            {insightLoading ? 'Analyzing...' : 'Generate Insights'}
          </button>
        </div>
        {insights ? (
          <div className="insights-container">
            <div className={`grade-badge grade-${insights.adherence_grade}`}>Grade: {insights.adherence_grade}</div>
            <p className="insight-assessment">{insights.overall_assessment}</p>
            <div className="data-list mt-4">
              {insights.insights?.map((ins: any, i: number) => (
                <div key={i} className={`data-row compact insight-${ins.type}`}>
                  <div>
                    <span className={`tag ${ins.priority}`}>{ins.priority.toUpperCase()}</span>
                    <strong style={{ marginLeft: '8px' }}>{ins.title}</strong>
                    <p className="row-subtitle">{ins.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state"><p>Click "Generate Insights" to get AI-powered analysis.</p></div>
        )}
      </div>

      {/* Schedule Optimization */}
      <div className="panel">
        <div className="panel-header-actions">
          <h3 className="panel-title"><Clock size={18} /> Schedule Optimization</h3>
          <button className="btn outline small" onClick={fetchOptimization} disabled={optLoading}>
            {optLoading ? 'Analyzing...' : 'Analyze Timing'}
          </button>
        </div>
        {optimization ? (
          <div>
            <p className="panel-desc">{optimization.summary}</p>
            {optimization.suggestions?.length > 0 && (
              <div className="data-list mt-4">
                {optimization.suggestions.map((s: any, i: number) => (
                  <div key={i} className="data-row compact">
                    <div>
                      <strong>{s.medication}</strong>
                      <p className="row-subtitle">
                        Move from <strong>{s.current_time}</strong> → <strong>{s.suggested_time}</strong>
                        <br />{s.reason} (Avg delay: {s.avg_delay_minutes} min, {s.data_points} data points)
                      </p>
                    </div>
                    <span className={`tag ${s.confidence}`}>{s.confidence}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state"><p>Click "Analyze Timing" to detect scheduling patterns.</p></div>
        )}
      </div>
    </div>
  );
}

// ── Feature 4: Side Effects Tab ────────────────────────────────────────────

function SideEffectsTab({ patientId }: { patientId: number }) {
  const [symptom, setSymptom] = useState('');
  const [severity, setSeverity] = useState('mild');
  const [logs, setLogs] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchLogs(); }, [patientId]);

  const fetchLogs = async () => {
    try {
      const res = await axios.get(`/api/symptoms/${patientId}`);
      setLogs(res.data);
    } catch (e) { console.error(e); }
  };

  const logSymptom = async () => {
    if (!symptom.trim()) return;
    await axios.post(`/api/symptoms/${patientId}`, { symptom: symptom.trim(), severity });
    setSymptom('');
    fetchLogs();
    hotToast.success("Symptom logged");
  };

  const analyzeSymptoms = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/symptoms/${patientId}/analyze`);
      setAnalysis(res.data);
    } catch (e) { hotToast.error("Analysis failed"); }
    setLoading(false);
  };

  return (
    <div className="two-col-grid">
      {/* Log Symptom */}
      <div className="panel">
        <h3 className="panel-title"><Thermometer size={18} /> Log a Symptom</h3>
        <p className="panel-desc">Record any symptoms the patient is experiencing.</p>
        <div className="form-group mt-4">
          <label>Symptom</label>
          <input type="text" className="form-input" placeholder="e.g. Dizziness, Nausea, Headache" value={symptom} onChange={e => setSymptom(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Severity</label>
          <select className="form-input" value={severity} onChange={e => setSeverity(e.target.value)}>
            <option value="mild">Mild</option>
            <option value="moderate">Moderate</option>
            <option value="severe">Severe</option>
          </select>
        </div>
        <button className="btn primary full-width" onClick={logSymptom} disabled={!symptom.trim()}>Log Symptom</button>
        <button className="btn outline full-width mt-4" onClick={analyzeSymptoms} disabled={loading || logs.length === 0}>
          {loading ? 'Analyzing...' : '🔬 Analyze Correlations with AI'}
        </button>
      </div>

      {/* Symptom History */}
      <div className="panel">
        <h3 className="panel-title">Symptom History</h3>
        {logs.length === 0 ? (
          <div className="empty-state"><p>No symptoms logged yet.</p></div>
        ) : (
          <div className="data-list" style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {logs.map((log: any) => (
              <div key={log.id} className="data-row compact">
                <div>
                  <strong>{log.symptom}</strong>
                  <span className={`tag ${log.severity}`} style={{ marginLeft: '8px' }}>{log.severity}</span>
                </div>
                <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                  {new Date(log.timestamp).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Analysis */}
      {analysis && (
        <div className="panel col-span-2">
          <h3 className="panel-title">🔬 AI Correlation Analysis</h3>
          <p className="panel-desc">{analysis.summary}</p>
          {analysis.correlations?.length > 0 ? (
            <div className="data-list mt-4">
              {analysis.correlations.map((c: any, i: number) => (
                <div key={i} className={`data-row compact correlation-${c.likelihood}`}>
                  <div>
                    <span className={`tag ${c.likelihood}`}>{c.likelihood.toUpperCase()}</span>
                    <strong style={{ marginLeft: '8px' }}>{c.symptom} ↔ {c.medication}</strong>
                    <p className="row-subtitle">{c.evidence}</p>
                    <p className="row-subtitle" style={{ fontStyle: 'italic' }}>💡 {c.recommendation}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted mt-4">No correlations found between reported symptoms and active medications.</p>
          )}
          {analysis.consult_doctor && (
            <div className="action-required-box mt-4">
              <strong>⚕️ Doctor Consultation Recommended</strong> — Based on the analysis, we recommend discussing these symptoms with the prescribing doctor.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Feature 1: Chat Tab ──────────────────────────────────────────────────

function ChatTab({ patientId }: { patientId: number }) {
  const [messages, setMessages] = useState<any[]>([
    { role: 'assistant', content: "Hello! I'm your MedAgent AI Assistant. Ask me anything about this patient's medications, schedule, or adherence. For example:\n\n• \"What medicines are active?\"\n• \"Did they miss any doses today?\"\n• \"How is their adherence this week?\"" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', content: m.content }));
      const res = await axios.post('/api/chat', {
        patient_id: patientId,
        message: userMsg,
        history
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.reply,
        tools: res.data.tools_used
      }]);
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm sorry, I couldn't process that request. Please try again."
      }]);
    }
    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
            </div>
            <div className="chat-content">
              <p>{msg.content}</p>
              {msg.tools?.length > 0 && (
                <div className="chat-tools">
                  {msg.tools.map((t: any, j: number) => (
                    <span key={j} className="tool-badge">🔧 {t.tool.replace('get_', '').replace(/_/g, ' ')}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant">
            <div className="chat-avatar"><Bot size={18} /></div>
            <div className="chat-content"><div className="typing-indicator"><span></span><span></span><span></span></div></div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>
      <div className="chat-input-bar">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask about medications, schedule, adherence..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
        />
        <button className="btn primary chat-send" onClick={sendMessage} disabled={loading || !input.trim()}>
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}

// ── Existing: Reminders & Reports ──────────────────────────────────────────

function RemindersTab({ patientId }: { patientId: number }) {
  const [log, setLog] = useState<string[]>([]);

  const addLog = (msg: string) => setLog(prev => [msg, ...prev]);

  const runScheduler = async () => {
    addLog("Triggering Scheduler Agent...");
    const res = await axios.post(`/api/scheduler/${patientId}`);
    addLog(res.data.note || `Sent ${res.data.reminders?.length || 0} reminders.`);
  };

  const runMonitor = async () => {
    addLog("Triggering Monitor Agent...");
    const res = await axios.post(`/api/monitor/${patientId}`);
    addLog(res.data.note || `Monitor completed. Required ${res.data.actions?.length || 0} actions.`);
  };

  return (
    <div className="two-col-grid">
      <div className="panel">
        <h3 className="panel-title">Trigger Agents</h3>
        <p className="panel-desc">Manually trigger backend autonomous agents.</p>
        <div className="action-stack mt-4">
          <button className="btn primary" onClick={runScheduler}>Run Scheduler Agent</button>
          <button className="btn primary" onClick={runMonitor}>Run Monitor Agent</button>
        </div>
      </div>
      <div className="panel console-panel">
        <h3 className="panel-title">Agent Execution Logs</h3>
        <div className="console-output">
          {log.length === 0 ? <span className="text-muted">No recent executions...</span> :
            log.map((line, i) => <div key={i} className="console-line">&gt; {line}</div>)
          }
        </div>
      </div>
    </div>
  );
}

function ReportsTab({ patientId }: { patientId: number }) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generateReport = async (type: string) => {
    setLoading(true);
    const res = await axios.get(`/api/report/${patientId}?type=${type}`);
    setReport(res.data);
    setLoading(false);
  };

  return (
    <div className="two-col-grid">
      <div className="panel">
        <h3 className="panel-title">Caregiver Report Agent</h3>
        <p className="panel-desc">Generates plain-language adherence summaries tailored for caregivers.</p>
        <div className="action-stack mt-4">
          <button className="btn outline" onClick={() => generateReport('daily')} disabled={loading}>Generate Daily Report</button>
          <button className="btn outline" onClick={() => generateReport('weekly')} disabled={loading}>Generate Weekly Report</button>
        </div>
      </div>

      {report && (
        <div className={`panel col-span-2 ${report.action_needed ? 'alert-moderate' : ''}`}>
          <h3 className="panel-title">{report.headline}</h3>
          <p className="report-text">{report.summary}</p>
          {report.action_needed && (
            <div className="action-required-box mt-4">
              <strong>Action Required:</strong> {report.recommended_action}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Modals ───────────────────────────────────────────────────────────────

function AddPatientModal({ onClose, onSuccess }: { onClose: () => void, onSuccess: (id: number) => void }) {
  const [formData, setFormData] = useState({ name: '', age: '', caregiver_name: '', caregiver_email: '', caregiver_mobile: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post('/api/patients', {
        ...formData,
        age: parseInt(formData.age) || 0
      });
      onSuccess(res.data.id);
      hotToast.success("Patient added successfully");
    } catch (err: any) {
      hotToast.error(err.response?.data?.detail || "Failed to add patient");
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Add New Patient</h3>
          <button className="icon-btn" onClick={onClose}><XCircle size={20} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Patient Name</label>
            <input required type="text" className="form-input" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Age</label>
            <input type="number" className="form-input" value={formData.age} onChange={e => setFormData({ ...formData, age: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Caregiver Name</label>
            <input type="text" className="form-input" value={formData.caregiver_name} onChange={e => setFormData({ ...formData, caregiver_name: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Caregiver Email</label>
            <input type="email" className="form-input" value={formData.caregiver_email} onChange={e => setFormData({ ...formData, caregiver_email: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Caregiver Mobile</label>
            <input type="text" className="form-input" value={formData.caregiver_mobile} onChange={e => setFormData({ ...formData, caregiver_mobile: e.target.value })} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn primary" disabled={loading}>{loading ? 'Saving...' : 'Save Patient'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
