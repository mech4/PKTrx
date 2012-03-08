class fSummaryInvestment:
  def __init__(self, formObj, parentForm):
    self.app = formObj.ClientApplication
    self.userapp = self.app.UserAppObject
    self.oPrint = self.app.GetClientClass('PrintLib','PrintLib')()

  def Show(self):
    #-- Set Branch Filter
    uipData = self.uipData
    uipData.Edit()
    IsHeadOffice = (uipData.BranchCode == uipData.HeadOfficeCode)
    self.MasterBranchCode = ''
    
    if not IsHeadOffice :
      uipData.MasterBranchCode = uipData.BranchCode

    uipData.SetFieldValue('LBranch.BranchCode',uipData.BranchCode)
    uipData.SetFieldValue('LBranch.BranchName',uipData.BranchName)
    
    return self.FormContainer.Show()

  def PrintExcelClick(self,sender) :
    uipData = self.uipData
    app = self.FormObject.ClientApplication
    
    if self.uipData.BeginDate > self.uipData.EndDate :
       raise 'PERINGATAN','Tanggal Awal tidak boleh lebih besar dari tanggal akhir'

    filename = self.oPrint.ConfirmDestinationPath(self.app,'xls')
    if filename in ['',None] : return


    self.FormObject.CommitBuffer()
    
    # -- Generate Param
    #ph = self.FormObject.GetDataPacket()
    BranchCode = uipData.GetFieldValue('LBranch.BranchCode')
    BeginDate = uipData.BeginDate
    EndDate = uipData.EndDate
    
    param = app.CreateValues(
      ['BranchCode',BranchCode],
      ['BeginDate',BeginDate],
      ['EndDate',EndDate]
    )
    ph = self.FormObject.CallServerMethod("SummaryInvestment", param)

    status = ph.FirstRecord
    if status.Is_Err : raise 'PERINGATAN',status.Err_Message
    
    ds = ph.packet.summary
    if ds.RecordCount <= 0 :
      self.app.ShowMessage('Tidak ada data untuk dicetak')
      return
      
    workbook = self.oPrint.OpenExcelTemplate(self.app,'tplSumInvestment.xls')
    try:
      workbook.ActivateWorksheet('DataRekap')
      BranchName = status.BranchName
      PeriodStr = status.PeriodStr

      workbook.SetCellValue(2, 2, '%s' % (BranchCode,BranchName))
      workbook.SetCellValue(3, 2, PeriodStr) # Nomor Karyawan
      workbook.SetCellValue(4, 2, status.BeginBalance) # Nomor Karyawan
      workbook.SetCellValue(5, 2, status.TotalDebet)
      workbook.SetCellValue(6, 2, status.TotalCredit)
      workbook.SetCellValue(7, 2, status.EndBalance)
      
      workbook.SetCellValue(9, 4, 'Saldo Awal \n' + status.BeginDateStr)
      workbook.SetCellValue(9, 8, 'Saldo Akhir \n' + status.EndDateStr)
      i = 0
      oldIdNumber = 0
      while i < ds.RecordCount:
        rec = ds.GetRecord(i)
        row = i + 10

        if oldIdNumber != rec.NomorKaryawan :
          workbook.SetCellValue(row, 1, rec.NomorKaryawan)
          workbook.SetCellValue(row, 2, rec.NamaKaryawan)
          oldIdNumber = rec.NomorKaryawan

        workbook.SetCellValue(row, 3, rec.CurrencyName)
        workbook.SetCellValue(row, 4, rec.SaldoAwal)
        workbook.SetCellValue(row, 5, rec.Debet)
        workbook.SetCellValue(row, 6, rec.Kredit)
        workbook.SetCellValue(row, 7, rec.TotalMutasi)
        workbook.SetCellValue(row, 8, rec.SaldoAkhir)
        i += 1
      # end of while


      # ---- Data Histori
      dsHistTrans = ph.packet.historitransaksi
      workbook.ActivateWorksheet('DetilTransaksi')

      workbook.SetCellValue(1, 2, status.TotalDebetHist)
      workbook.SetCellValue(2, 2, status.TotalCreditHist)

      i = 0
      TotalTransaksi = dsHistTrans.RecordCount
      while i < TotalTransaksi:
        rec = dsHistTrans.GetRecord(i)
        row = i + 5

        workbook.SetCellValue(row, 1, rec.TransactionDateStr)
        workbook.SetCellValue(row, 2, rec.TransactionNo)
        workbook.SetCellValue(row, 3, rec.AccountName)
        workbook.SetCellValue(row, 4, rec.MutationType)
        workbook.SetCellValue(row, 5, rec.Amount)
        workbook.SetCellValue(row, 6, rec.CurrencyName)
        workbook.SetCellValue(row, 7, rec.AmountEkuivalen)
        workbook.SetCellValue(row, 8, rec.ReferenceNo)
        workbook.SetCellValue(row, 9, rec.Description)
        workbook.SetCellValue(row, 10, rec.Inputer)

        i += 1
      # end while

      workbook.SaveAs(filename)
      self.app.ShellExecuteFile(filename)

    finally:
      workbook = None

    return 1

