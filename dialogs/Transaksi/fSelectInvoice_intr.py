class fSelectInvoice:
  def __init__(self,formObj,parentForm):
    self.form = formObj
    self.app = formObj.ClientApplication
    self.TransactionItemId = 0
    self.Amount = 0.0
    self.Description = ''
    self.Tgl = None
    self.TransactionItemId = None
    self.TransactionNo = None
    self.TransactionDate = None
    self.Amount = None
    self.Description = None

  def GetTransaction(self,BranchCode):
    self.uipFilter.Edit()
    self.DisplayTransaction()
    
    st = self.FormContainer.Show()
    if st == 1 :
      return 1

    return 0

  def Show(self):
    self.DisplayTransaction()
    self.FormContainer.Show()
    
  def bApplyClick(self,sender):
    self.DisplayTransaction()

  def DisplayTransaction(self):
    app = self.app
    uipFilter = self.uipFilter
    
    BeginY, BeginM, BeginD = uipFilter.BeginDate[:3]
    EndY, EndM, EndD = uipFilter.EndDate[:3]
    intBeginDate = app.ModDateTime.EncodeDate(BeginY,BeginM,BeginD)
    sBegin = '%s-%s-%s' % (str(BeginM).zfill(2),str(BeginD).zfill(2),str(BeginY))
    intEndDate = app.ModDateTime.EncodeDate(EndY,EndM,EndD)
    sEnd = '%s-%s-%s' % (str(EndM).zfill(2),str(EndD).zfill(2),str(EndY))

    self.form.SetDataFromQuery('uipInvoice',
         " \
         BranchCode = '%s'  \
         and InvoiceDate >= '%s' \
         and InvoiceDate <= '%s' \
         and InvoicePaymentStatus = 'F' \
         " % (uipFilter.BranchCode,sBegin,sEnd), '')
    return

  def GridDoubleClick(self,sender):
    self.ProsesClick(self.pAction_bPilih)

  def Check(self):
    pass
    
  def ProsesClick(self,sender):
    self.Check()
    self.FormObject.Close(1)
