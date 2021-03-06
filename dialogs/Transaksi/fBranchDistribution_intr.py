KodeTransaksi = ['KK','KM']

class fBranchDistribution:
  def __init__(self, formObj, parentForm) :
    self.app = formObj.ClientApplication
    self.fSearchEmployee = None
    self.fSearchBudget = None
    self.fSelectProduct = None

  def Show(self , mode = 1):
    uipTran = self.uipTransaction
    uipTran.Edit()
    uipTran.ShowMode = mode
    if mode == 1 : # Insert Mode
      uipTran.FundEntity = 4
    
    self.SetFundEntitySource(uipTran.FundEntity)
    
    return self.FormContainer.Show()

  def BatchAfterLookup(self, sender, linkui):
    uipTran = self.uipTransaction
    uipTran.Edit()
    uipTran.ActualDate = uipTran.GetFieldValue('LBatch.BatchDate')
    
  def LCashDestBeforeLookup(self, sender, linkui):
    uipTran = self.uipTransaction

    if uipTran.BranchCodeDestination in ['',None] :
      raise 'PERINGATAN','Pilih Dahulu Cabang Tujuan'
      
    return 1

  def FundEntityOnChange(self,sender):
    self.SetFundEntitySource(sender.ItemIndex + 1)

  def SetFundEntitySource(self, FundEntity):
    uipTran = self.uipTransaction
    
    # enable jika jenis dana selain amil
    self.pTransaction_bSelectProduct.enabled = ( FundEntity != 4 )

    if FundEntity == 4 :
      uipTran.Edit()
      uipTran.AccountNo = ''
      uipTran.AccountName = ''


  def EmployeeAfterLookup (self, sender, linkui):
    self.uipTransaction.EmployeeName = self.uipTransaction.GetFieldValue('LEmployee.Nama_Lengkap')

  def BranchDestAfterLookup(self,sender,linkui):
    self.uipTransaction.Edit()
    self.uipTransaction.BranchCodeDestination = self.uipTransaction.GetFieldValue('LBranchDestination.BranchCode')
    
  def SearchEmployeeClick(self,sender):
    if self.fSearchEmployee == None:
      formname = 'Transaksi/fSearchEmployee'
      form = self.app.CreateForm(formname,formname,0,None,None)
      self.fSearchEmployee = form
    else:
      form = self.fSearchEmployee
    # end if

    if form.ShowData():
      uipTran = self.uipTransaction
      uipTran.EmployeeName = form.uipEmployee.EmployeeName
      uipTran.EmployeeId = form.uipEmployee.EmployeeId
    # end if
    
  def bSearchBudgetClick(self, sender):
    uipTran = self.uipTransaction
    if self.fSearchBudget == None:
      formname = 'Transaksi/fSelectBudgetCode'
      form = self.app.CreateForm(formname,formname,0,None,None)
      self.fSearchBudget = form
    else:
      form = self.fSearchBudget
    # end if

    ActualDate = self.uipTransaction.ActualDate or 0
    if ActualDate == 0 :
      raise 'Peringatan','Tanggal transaksi belum diinput. Silahkan input tanggal transaksi lebih dahulu'

    if form.GetBudget(ActualDate) == 1:
      uipTran.Edit()
      uipTran.BudgetCode = form.BudgetCode
      uipTran.BudgetOwner = form.BudgetOwner
      uipTran.BudgetId = form.BudgetId
    # end if

  def bSelectProductClick(self,sender):
    if self.fSelectProduct == None:
      fData = self.app.CreateForm('Transaksi/fSelectProgram', 'Transaksi/fSelectProgram', 0, None, None)
      self.fSelectProduct = fData
    else:
      fData = self.fSelectProduct
    # end if
    
    branchCode = self.uipTransaction.BranchCode
    if fData.GetProduct(branchCode) == 1:

      #productId = fData.ProductId
      #productName = fData.ProductName
      #fundCategory = fData.FundCategory
      #AccountNo = fData.AccountNo
      #fundEntity = MAPEntity[fData.FundCategory or 'I']

      #self.uipTransactionItem.Edit()
      #self.uipTransactionItem.SetFieldValue('LProduct.ProductId', productId)
      #self.uipTransactionItem.SetFieldValue('LProduct.ProductName', productName)
      #self.uipTransactionItem.SetFieldValue('LProduct.FundCategory', fundCategory)
      #self.uipTransactionItem.FundEntity = fundEntity
      #self.uipTransactionItem.AccountNo = AccountNo
      #self.uipTransactionItem.Description = productName
      uipTran = self.uipTransaction
      uipTran.Edit()
      uipTran.AccountNo = fData.AccountNo
      uipTran.AccountName = fData.ProductName
      uipTran.Description = fData.ProductName

      #if fundEntity != 1:
      #  self.uipTransactionItem.Ashnaf = 'L'

    return 1

  def CheckRequired(self):
    uipTran = self.uipTransaction

    if uipTran.ActualDate in [0, None] :
      raise 'PERINGATAN','Tanggal Transaksi belum diinputkan'

    if uipTran.GetFieldValue('LCashAccount.AccountNo') in ['', None] :
      raise 'PERINGATAN','Kas / Bank Pengirim Belum diinputkan'

    if uipTran.GetFieldValue('LCashAccountDestination.AccountNo') in ['', None] :
      raise 'PERINGATAN','Kas / Bank Penerima Belum diinputkan'
      
    if uipTran.FundEntity in [None, '' ]:
      raise 'PERINGATAN', 'Jenis Sumber Dana Belum dipilih'
      
    if uipTran.FundEntity != 4 :
      if uipTran.AccountNo in ['', None] :
        raise 'PERINGATAN','Program / Project Belum diinputkan'

    if (uipTran.Amount or 0.0) <= 0.0:
      raise 'PERINGATAN','Nilai Transaksi tidak boleh <= 0.0 '


  def bSimpanClick(self, sender):
    app = self.app
    
    self.CheckRequired()
    
    if app.ConfirmDialog('Yakin simpan transaksi ?'):
      self.FormObject.CommitBuffer()
      ph = self.FormObject.GetDataPacket()

      ph = self.FormObject.CallServerMethod("SimpanData", ph)
      res = ph.FirstRecord
      if res.IsErr == 1:
        app.ShowMessage(res.ErrMessage)
        sender.ExitAction = 0
      else:
        Message = 'Transaksi Berhasil.\nNomor Transaksi : ' + res.TransactionNo
        if res.IsErr == 2:
          Message += '\n Proses Jurnal Gagal.' + res.ErrMessage

        app.ShowMessage(Message)
        if app.ConfirmDialog('Apakah akan cetak kwitansi ?'):
          oPrint = app.GetClientClass('PrintLib','PrintLib')()
          oPrint.doProcessByStreamName(app,ph.packet,res.StreamName)

        sender.ExitAction = 1
    #-- if
