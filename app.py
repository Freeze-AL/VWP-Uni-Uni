import streamlit as st
import pandas as pd
import sqlite3, io, zipfile, shutil
from datetime import date, datetime
from pathlib import Path
from PIL import Image
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
ROOT=Path(__file__).parent
DB=ROOT/'monitoring.db'; PHOTO=ROOT/'photos';PHOTO.mkdir(exist_ok=True)
con=sqlite3.connect(DB,check_same_thread=False)
con.execute('CREATE TABLE IF NOT EXISTS sensors (id TEXT PRIMARY KEY,serial TEXT,f0 REAL,t0 REAL,k REAL,b REAL,elevation REAL,sigma_v REAL,notes TEXT)')
con.execute('CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT,sensor TEXT,day TEXT,freq REAL,temp REAL,m REAL,head REAL,pressure REAL,ru REAL,photo TEXT,notes TEXT,created TEXT)')
con.commit()
def calc(s,f,t):
 m=f*f/1000; m0=s['f0']**2/1000
 numerator=s['k']*(m-m0)+s['b']*(t-s['t0'])
 head=numerator/9.81
 pressure=head/9.81*101.325 # exact workbook formula; confirm units with instrument calibration
 ru=pressure/s['sigma_v'] if s['sigma_v'] and s['sigma_v']>0 else None
 return m,head,pressure,ru
def sensors():return pd.read_sql_query('SELECT * FROM sensors ORDER BY id',con)
def readings():return pd.read_sql_query('SELECT * FROM readings ORDER BY day,id',con)
st.set_page_config(page_title='VWP Monitoring',page_icon='💧',layout='wide')
st.title('💧 VWP Monitoring & Pore Pressure Ratio')
st.caption('Streamlit saja • SQLite lokal • input frekuensi & suhu • laporan dan foto')
st.warning('Jika dihosting di Streamlit Community Cloud, data baru dan foto dapat hilang saat aplikasi restart/redeploy. Unduh backup ZIP secara berkala dan pulihkan dengan menu Backup & Restore. Jangan gunakan sebagai penyimpanan permanen produksi.')
with st.sidebar:
 st.header('Menu')
 page=st.radio('Halaman',['Dashboard','Input pembacaan','Pengaturan instrumen','Riwayat & laporan','Backup & Restore'])
 st.info('Ru = tekanan air pori (kPa) / tegangan vertikal total (kPa). Tetapkan sigma_v tiap instrumen terlebih dahulu.')
ss=sensors();rr=readings()
if page=='Pengaturan instrumen':
 st.subheader('Parameter instrumen (diisi satu kali)')
 if not ss.empty:st.dataframe(ss,use_container_width=True,hide_index=True)
 with st.form('sensor'):
  sid=st.text_input('Kode titik VWP (baru / yang akan diperbarui)')
  a,b=st.columns(2)
  with a:
   serial=st.text_input('Nomor seri');f0=st.number_input('F0 (Hz)',value=2300.0,format='%.4f');t0=st.number_input('T0 (°C)',value=30.0)
  with b:
   k=st.number_input('k',value=-0.35,format='%.6f');coef=st.number_input('b',value=-2.0,format='%.6f');elev=st.number_input('Elevasi titik (m)',value=0.0)
  sigma=st.number_input('Tegangan vertikal total σv (kPa) — 0 jika belum diketahui',min_value=0.0,value=0.0)
  note=st.text_area('Catatan / dasar perhitungan σv')
  if st.form_submit_button('Simpan instrumen',type='primary'):
   if not sid.strip():st.error('Kode titik wajib diisi')
   else:
    con.execute('INSERT OR REPLACE INTO sensors VALUES (?,?,?,?,?,?,?,?,?)',(sid.strip(),serial,f0,t0,k,coef,elev,sigma,note));con.commit();st.success('Parameter tersimpan');st.rerun()
elif page=='Input pembacaan':
 if ss.empty:st.warning('Tambahkan instrumen pada Pengaturan instrumen terlebih dahulu.')
 else:
  with st.form('reading'):
   c1,c2,c3=st.columns(3)
   with c1: sid=st.selectbox('Titik VWP',ss.id.tolist());day=st.date_input('Tanggal',date.today())
   with c2:f=st.number_input('Frekuensi (Hz)',min_value=0.01,value=2300.0,format='%.3f')
   with c3:t=st.number_input('Suhu (°C)',value=30.0,format='%.2f')
   photo=st.file_uploader('Foto dokumentasi',type=['jpg','jpeg','png']);note=st.text_area('Keterangan / kondisi lapangan')
   save=st.form_submit_button('Hitung & simpan',type='primary')
  s=ss.set_index('id').loc[sid];m,h,p,ru=calc(s,f,t)
  c1,c2,c3=st.columns(3);c1.metric('Water head (m)',f'{h:.4f}');c2.metric('Pore pressure (kPa)',f'{p:.4f}');c3.metric('Ru',f'{ru:.4f}' if ru is not None else 'Belum tersedia')
  if ru is None:st.warning('Isi tegangan vertikal total σv pada pengaturan instrumen untuk menghitung Ru.')
  if save:
   path=''
   if photo:
    ext=Path(photo.name).suffix.lower();path=str(PHOTO/f'{sid}_{datetime.now():%Y%m%d_%H%M%S_%f}{ext}');Path(path).write_bytes(photo.getvalue())
   con.execute('INSERT INTO readings (sensor,day,freq,temp,m,head,pressure,ru,photo,notes,created) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(sid,day.isoformat(),f,t,m,h,p,ru,path,note,datetime.now().isoformat()));con.commit();st.success('Pembacaan tersimpan')
elif page=='Backup & Restore':
 st.subheader('Backup seluruh data dan foto')
 st.info('Simpan file backup di HP/laptop setiap selesai monitoring. Untuk memulihkan data setelah aplikasi restart, upload ZIP backup di sini.')
 def make_backup():
  con.commit()
  mem=io.BytesIO()
  with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_DEFLATED) as z:
   z.write(DB,'monitoring.db')
   for f in PHOTO.iterdir():
    if f.is_file():z.write(f,'photos/'+f.name)
  return mem.getvalue()
 st.download_button('⬇️ Download backup ZIP',make_backup(),f'backup_vwp_{date.today()}.zip','application/zip',type='primary')
 uploaded=st.file_uploader('Pilih backup ZIP untuk restore',type=['zip'])
 confirm=st.checkbox('Saya memahami restore akan mengganti database dan foto yang ada sekarang')
 if st.button('Pulihkan backup',disabled=not(uploaded and confirm)):
  try:
   with zipfile.ZipFile(io.BytesIO(uploaded.getvalue())) as z:
    names=z.namelist()
    if 'monitoring.db' not in names:raise ValueError('File monitoring.db tidak ditemukan')
    tmp=ROOT/'restore_check.db';tmp.write_bytes(z.read('monitoring.db'))
    check=sqlite3.connect(tmp)
    ok=check.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    tables={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check.close()
    if not ok or not {'sensors','readings'}.issubset(tables):raise ValueError('Database backup tidak valid')
    con.close();shutil.copyfile(tmp,DB);tmp.unlink(missing_ok=True)
    for f in PHOTO.iterdir():
     if f.is_file():f.unlink()
    for name in names:
     if name.startswith('photos/') and not name.endswith('/') and '/' not in name[7:]:
      (PHOTO/Path(name).name).write_bytes(z.read(name))
   st.success('Restore berhasil. Refresh halaman untuk melihat data.')
  except Exception as e:st.error(f'Restore gagal: {e}')
elif page=='Dashboard':
 if rr.empty:st.info('Belum ada pembacaan. Masukkan data melalui menu Input pembacaan.')
 else:
  latest=rr.sort_values(['day','id']).groupby('sensor').tail(1)
  c1,c2,c3=st.columns(3);c1.metric('Titik termonitor',latest.sensor.nunique());c2.metric('Total pembacaan',len(rr));c3.metric('Ru tersedia',int(latest.ru.notna().sum()))
  st.subheader('Kondisi terakhir per titik');st.dataframe(latest[['sensor','day','freq','temp','pressure','ru']],hide_index=True,use_container_width=True)
  sid=st.selectbox('Grafik titik',sorted(rr.sensor.unique()));sub=rr[rr.sensor==sid].copy();sub['tanggal']=pd.to_datetime(sub.day)
  st.subheader('Tekanan air pori (kPa)');st.line_chart(sub.set_index('tanggal')['pressure'])
  st.subheader('Pore Pressure Ratio (Ru)');st.line_chart(sub.set_index('tanggal')['ru'])
else:
 st.subheader('Riwayat pembacaan dan laporan')
 if rr.empty:st.info('Belum ada data.')
 else:
  opts=['Semua titik']+sorted(rr.sensor.unique());sel=st.selectbox('Filter titik',opts)
  sub=rr if sel=='Semua titik' else rr[rr.sensor==sel]
  st.dataframe(sub[['sensor','day','freq','temp','m','head','pressure','ru','notes']],hide_index=True,use_container_width=True)
  st.download_button('Unduh CSV',sub.to_csv(index=False).encode('utf-8-sig'),'vwp_monitoring.csv','text/csv')
  def pdf_report():
   buf=io.BytesIO();doc=SimpleDocTemplate(buf,pagesize=(842,595),leftMargin=35,rightMargin=35);styles=getSampleStyleSheet()
   story=[Paragraph('VWP MONITORING REPORT',styles['Title']),Paragraph(f'Filter: {sel} | Dibuat: {date.today()}',styles['Normal']),Spacer(1,14)]
   rows=[['Titik','Tanggal','Freq (Hz)','Suhu (C)','Head (m)','P (kPa)','Ru']]
   for _,r in sub.iterrows():rows.append([str(r.sensor),str(r.day),f'{r.freq:.2f}',f'{r.temp:.2f}',f'{r["head"]:.3f}',f'{r.pressure:.3f}',f'{r.ru:.4f}' if pd.notna(r.ru) else '-'])
   for start in range(1,len(rows),28):
    tab=Table([rows[0]]+rows[start:start+28],repeatRows=1,colWidths=[105,95,90,80,90,90,75]);tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf5')),('GRID',(0,0),(-1,-1),0.3,colors.grey),('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(tab);story.append(Spacer(1,12))
   story.append(Paragraph('Catatan: Ru hanya dihitung apabila sigma_v telah ditentukan. Formula tekanan mengikuti file Excel sumber dan perlu validasi satuan.',styles['Normal']))
   doc.build(story);return buf.getvalue()
  st.download_button('Unduh laporan PDF',pdf_report(),'laporan_vwp.pdf','application/pdf')
  st.subheader('Foto dokumentasi')
  for _,r in sub[sub.photo.fillna('')!=''].tail(12).iloc[::-1].iterrows():
   if Path(r.photo).exists():
    with st.expander(f'{r.sensor} • {r.day}'):
     st.image(r.photo,width=420);st.write(r.notes or '-')
