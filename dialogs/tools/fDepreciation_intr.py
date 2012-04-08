class fDepreciation:
  def __init__(self,formObj,parentForm):
    self.app = formObj.ClientApplication
    self.form = formObj
    
  def Show(self):
    self.FormContainer.Show()
    
    """
    uipData = self.uipData
    self.form.CommitBuffer()

    if (uipData.ProcessDate or '') == '' :
      raise 'PERINGATAN','Anda belum memasukkan tanggal proses tutup buku'

    if self.app.ConfirmDialog('Anda yakin akan melakukan proses tutup buku ?'):

      pid = self.app.ExecuteScriptTrackable('POD/L_CloseDay', None)

      pcConsole = self.pcConsole
      pcConsole.ConsoleFilterName = 'closeday_' + str(pid)
      pcConsole.ShowStatusBar = 0
      pcConsole.Headerless = 0
      pcConsole.Activate()
    
    return"""

  def ProcessClick(self,sender):
    uipData = self.uipData
    self.form.CommitBuffer()
    
    if (uipData.ProcessDate or '') == '' :
      raise 'PERINGATAN','Anda belum memasukkan tanggal batas penysutan'
      
    if self.app.ConfirmDialog('Anda yakin akan melakukan proses penyusutan nilai aset ?'):
      #rph = self.app.ExecuteScript("")
      rph = self.app.ExecuteScript("Tools/L_Depreciation",self.form.GetDataPacket())

      status = rph.FirstRecord
      if status.Is_Err :
        raise 'PERINGATAN',status.Err_Message

      self.app.ShowMessage('Proses Penyusutan Berhasil')

      sender.ExitAction = 1
