# GeneralTransaction.py
import simplejson
import com.ihsan.foundation.pobjecthelper as phelper

status = 0
msg = ''
FileKwitansi = ''

def GenerateResponse(Status,ErrMessage,TransactionNo,FileKwitansi):
  response = {}
  response['Status'] = Status
  response['TransactionNo'] = TransactionNo
  response['ErrMessage'] = ErrMessage
  response['FileKwitansi'] = FileKwitansi
  
  return simplejson.dumps(response)

def CreateAssetPaymentTransaction(oTran,oAsset,Amount,Description):
  if oAsset.LAssetCategory.AssetType == 'T' :      
    oProduct = oAsset.LProductAccount
    
    oItemFA = oTran.CreateAccountTransactionItem(oProduct)
    oItemFA.SetMutation('D',Amount,1.0)
    oItemFA.Description = Description
    oItemFA.SetJournalParameter('DA02A')
    oItemFA.SetDistributionEntity(2)
  else:
    oItemFA = oTran.CreateGLTransactionItem('5210201', '000')
    oItemFA.RefAccountName = 'Penyaluran Infaq/ Shodaqoh Tidak Terikat'
    oItemFA.SetMutation('D',Amount,1.0)
    oItemFA.Description = Description
    oItemFA.SetJournalParameter('DA02B')
  return oItemFA

def FixedAssetNew(config, srequest,params):
  request = simplejson.loads(srequest)
  helper = phelper.PObjectHelper(config)

  status = 0
  msg = ''
   
  config.BeginTransaction()
  try:
    oBatch = helper.GetObject('TransactionBatch', request[u'BatchId'])
    oTran = oBatch.NewTransaction('FA')
    
    FileKwitansi = FixAsset(helper,oTran,oBatch,request,params)    
        
    # Check for auto approval
    corporate = helper.CreateObject('Corporate')
    if corporate.CheckLimitOtorisasi(request[u'Amount']):
      oTran.AutoApproval()
      
    config.Commit()
  except:
    config.Rollback()
    raise
  
  status,msg = oTran.CreateJournal()      
  return GenerateResponse(status,msg,oTran.TransactionNo,FileKwitansi)

def FixedAssetUpdate(config,srequest ,params):
  request = simplejson.loads(srequest)
  helper = phelper.PObjectHelper(config)
  
  oTran = helper.GetObjectByNames(
      'Transaction',{'TransactionNo': request[u'TransactionNo'] }
    )
  
  TranHelper = helper.LoadScript('Transaction.TransactionHelper')
  TranHelper.DeleteTransactionJournal(oTran)

  status = 0
  msg = ''
  
  config.BeginTransaction()
  try:
    oTran.CancelTransaction()
    oBatch = helper.GetObject('TransactionBatch', request[u'BatchId'])
    oTran.BatchId = oBatch.BatchId
    
    FileKwitansi = FixAsset(helper,oTran,oBatch,request,params)
    
    # Check for auto approval
    oTran.AutoApprovalUpdate()
    
    config.Commit()
  except:
    config.Rollback()
    raise

  status,msg = oTran.CreateJournal()      
  return GenerateResponse(status,msg,oTran.TransactionNo,FileKwitansi)  
 
def FixAsset(helper,oTran,oBatch,request,params):
  CashAdvance = request[u'CashAdvance']
  PaymentType = request[u'PaymentType']

  # 1. Set Data Transaksi    
  oTran.ReferenceNo = request[u'ReferenceNo']
  oTran.Description = request[u'Description']
  oTran.Inputer     = request[u'Inputer']
  oTran.BranchCode  = request[u'BranchCode']
  oTran.Amount = request[u'Amount']
  oTran.CurrencyCode = '000'
  #oTran.ReceivedFrom = request[u'ReceivedFrom']
  oTran.ActualDate = oBatch.GetAsTDateTime('BatchDate')

  # 2. Create/Replace Data FixedAsset
  AccountNoFA = str(request[u'FixAssetAccountNo'])
  if AccountNoFA == '' :
    oFAAccount = helper.CreatePObject('FixedAsset')
  else :
    oFAAccount = helper.GetObject('FixedAsset',AccountNoFA)
    
  oFAAccount.BranchCode = request[u'BranchCode']
  oFAAccount.CurrencyCode = '000'
  oFAAccount.AccountName  = request[u'AssetName']
  oFAAccount.Qty = request[u'Qty']
  oFAAccount.SetAssetCategory(request[u'AssetCategoryId'])
  oFAAccount.SetInitialValue(request[u'Amount'])
  oFAAccount.SetInitialProcessDate()
  oFAAccount.UangMuka = CashAdvance
  
  # Set Product Account jika asset terikat
  if oFAAccount.LAssetCategory.AssetType == 'T' :
    oFAAccount.AccountNoProduct = request[u'ProductAccountNo']

  
  # 3. Buat transaksi pembelian asset
  # Set Journal Code berdasarkan PaymentType
  if PaymentType == 'T' :
    JournalCode = 'DA01B'
  else :
    if CashAdvance > 0.0 :
      JournalCode = 'DA01A'
    else:
      JournalCode = 'DA01C'
    # endif
  # endif
             
  # Buat Transaksi pembelian
  oItemFA = oTran.CreateAccountTransactionItem(oFAAccount)
  oItemFA.SetMutation('D', request[u'Amount'], 1.0)
  oItemFA.Description = request[u'Description']
  oItemFA.SetJournalParameter(JournalCode)
  oItemFA.AccountCode = oFAAccount.GetAssetAccount()
  
  # 4. Buat Transaksi BudgetTransaction
  aBudgetId = request[u'BudgetId'] 

  if aBudgetId != 0 :
    oBudget = helper.GetObject('Budget',aBudgetId)
    oItemFA.CreateBudgetTransaction(oBudget.BudgetId)
  # endif

  # 5. Buat Transaksi Pembayaran Uang muka / Tunai
  if CashAdvance > 0.0 :
    # Destination Transaction
    oCashAccount = helper.GetObject('CashAccount',
      str(request[u'CashAccountNo'])).CastToLowestDescendant()
    if oCashAccount.isnull:
      raise 'Cash/Bank', 'Rekening %s tidak ditemukan' % request[u'CashAccountNo']

    oItemCA = oTran.CreateAccountTransactionItem(oCashAccount)
    oItemCA.SetMutation('C', CashAdvance, 1.0)    
    oItemCA.Description = request[u'Description']
    oItemCA.SetJournalParameter('10')
    
    oFAAccount.TotalDibayar = CashAdvance
    
    # Set Transaksi Produk Jika asset adalah asset terikat
    CreateAssetPaymentTransaction(oTran, oFAAccount, CashAdvance, request[u'Description'])
    
  oTran.GenerateTransactionNumber('000')
  oTran.SaveInbox(params)
  FileKwitansi = oTran.GetKwitansi()
  
  return FileKwitansi

def Invoice(config, srequest,params):
  request = simplejson.loads(srequest)
  helper = phelper.PObjectHelper(config)

  status = 0
  msg = ''

  config.BeginTransaction()
  try:
    oBatch = helper.GetObject('TransactionBatch', request[u'BatchId'])
    oTran = oBatch.NewTransaction('FAI')

    oTran.ReferenceNo = request[u'ReferenceNo']
    oTran.Description = request[u'Description']
    oTran.Inputer     = request[u'Inputer']
    oTran.BranchCode  = request[u'BranchCode']
    oTran.Amount = request[u'Amount']
    oTran.CurrencyCode = '000'
    #oTran.ReceivedFrom = request[u'ReceivedFrom']
    oTran.ActualDate = oBatch.GetAsTDateTime('BatchDate')
    aValuta = '000'
    aAmount = request[u'Amount']
    aRate = 1.0

    # Fixed Asset Account
    AssetAccountNo = request[u'AssetAccountNo']    
    oFAAccount = helper.GetObject('FixedAsset',str(AssetAccountNo))
    
    #oItemFA = oTran.CreateAccountTransactionItem(oFAAccount)
    #oItemFA.SetMutation('D', request[u'Amount'], 1.0)
    #oItemFA.Description = request[u'Description']
    #oItemFA.SetJournalParameter('DA03A')
    #oItemFA.AccountCode = oFAAccount.GetAssetAccount()
    
    AccountCode = oFAAccount.GetLiabilityAccount()
    oAccount = helper.GetObject('Account',AccountCode)
    oItemGL = oTran.CreateGLTransactionItem(AccountCode, aValuta)
    oItemGL.RefAccountName = oAccount.Account_Name
    oItemGL.SetMutation('D', aAmount, aRate)
    oItemGL.Description = 'Invoice Aktiva'
    oItemGL.SetJournalParameter('DA03A')
    
    # Create Invoice
    oInvoiceFA = helper.CreatePObject('InvoiceFA')
    oInvoiceFA.AccountNo = AssetAccountNo
    oInvoiceFA.InvoiceNo = request[u'InvoiceNo']
    oInvoiceFA.InvoiceDate = oTran.ActualDate
    oInvoiceFA.InvoiceAmount = aAmount    

    oTran.GenerateTransactionNumber('000')
    oTran.SaveInbox(params)
    FileKwitansi = oTran.GetKwitansi()
        
    # Check for auto approval
    corporate = helper.CreateObject('Corporate')
    if corporate.CheckLimitOtorisasi(request[u'Amount']):
      oTran.AutoApproval()

    config.Commit()
  except:
    config.Rollback()
    raise

  status,msg = oTran.CreateJournal()      
  return GenerateResponse(status,msg,oTran.TransactionNo,FileKwitansi)
  
def InvoicePayment(config, srequest,params):
  request = simplejson.loads(srequest)
  helper = phelper.PObjectHelper(config)

  status = 0
  msg = ''

  config.BeginTransaction()
  try:
    oBatch = helper.GetObject('TransactionBatch', request[u'BatchId'])
    oTran = oBatch.NewTransaction('FAIP')

    oTran.ReferenceNo = request[u'ReferenceNo']
    oTran.Description = request[u'Description']
    oTran.Inputer     = request[u'Inputer']
    oTran.BranchCode  = request[u'BranchCode']
    oTran.Amount = request[u'Amount']
    oTran.CurrencyCode = '000'
    #oTran.ReceivedFrom = request[u'ReceivedFrom']
    oTran.ActualDate = oBatch.GetAsTDateTime('BatchDate')
    aValuta = '000'
    aAmount = request[u'Amount']
    aRate = 1.0

    # Cash Account 
    oCashAccount = helper.GetObject('CashAccount',
      str(request[u'CashAccountNo'])).CastToLowestDescendant()
    if oCashAccount.isnull:
      raise 'Cash/Bank', 'Rekening %s tidak ditemukan' % request[u'CashAccountNo']
  
    oItemCA = oTran.CreateAccountTransactionItem(oCashAccount)
    oItemCA.SetMutation('C', aAmount, 1.0)    
    oItemCA.Description = request[u'Description']
    oItemCA.SetJournalParameter('DA03B')
    
    # Get Invoice
    oInvoiceFA = helper.GetObjectByNames('InvoiceFA',{'InvoiceNo' : request[u'InvoiceNo']})
    oInvoiceFA.InvoicePaymentStatus = 'T'
    
    # Get FinancialAccount
    oFA = helper.GetObject('FixedAsset',str(request[u'FAAccountNo']))
    oProduct = oFA.LProductAccount
    
    oItemFA = oTran.CreateAccountTransactionItem(oProduct)
    oItemFA.SetMutation('D',aAmount,1.0)
    oItemFA.Description = request[u'Description']
    oItemFA.SetJournalParameter('DA02A')
    oItemFA.SetDistributionEntity(2)
    
    oFA.TotalDibayar += aAmount
    
#     oInvoiceFA.AccountNo = AssetAccountNo
#     oInvoiceFA.InvoiceNo = request[u'InvoiceNo']
#     oInvoiceFA.InvoiceDate = oTran.ActualDate

    oTran.GenerateTransactionNumber(oCashAccount.CashCode)
    oTran.SaveInbox(params)
    FileKwitansi = oTran.GetKwitansi()
        
    # Check for auto approval
    corporate = helper.CreateObject('Corporate')
    if corporate.CheckLimitOtorisasi(request[u'Amount']):
      oTran.AutoApproval()

    config.Commit()
  except:
    config.Rollback()
    raise

  status,msg = oTran.CreateJournal()
  return GenerateResponse(status,msg,oTran.TransactionNo,FileKwitansi)
  
def Disposal(config, srequest,params):
  request = simplejson.loads(srequest)
  helper = phelper.PObjectHelper(config)

  status = 0
  msg = ''

  config.BeginTransaction()
  try:
    oBatch = helper.GetObject('TransactionBatch', request[u'BatchId'])
    oTran = oBatch.NewTransaction('FAIP')

    oTran.ReferenceNo = request[u'ReferenceNo']
    oTran.Description = request[u'Description']
    oTran.Inputer     = request[u'Inputer']
    oTran.BranchCode  = request[u'BranchCode']
    oTran.Amount = request[u'Amount']
    oTran.CurrencyCode = '000'
    #oTran.ReceivedFrom = request[u'ReceivedFrom']
    oTran.ActualDate = oBatch.GetAsTDateTime('BatchDate')
    aValuta = '000'
    aAmount = request[u'Amount']
    aAssetValue = request[u'AssetValue'] 
    aRate = 1.0

    if  aAmount > aAssetValue : # Jual Untung
      JournalCode = 'DA07'
    elif aAmount < aAssetValue : # Jual Rugi
      JournalCode = 'DA06'
    else : # 
      JournalCode = 'DA08'
    # end if elif else
    
      
    # Fixed Asset Account
    oFAAccount = helper.GetObject('FixedAsset',str(request[u'AssetAccountNo']))

    oItemFA = oTran.CreateAccountTransactionItem(oFAAccount)
    oItemFA.SetMutation('C', aAssetValue, 1.0)
    oItemFA.Description = request[u'Description']
    oItemFA.SetJournalParameter(JournalCode)
    oItemFA.AccountCode = oFAAccount.GetAssetAccount()
    
    # Create Fixed Transaction Additional Info
    oFAAccount.CreateSellTransactInfo(oItemFA,aAmount)
    
    # Cash Account
    oCashAccount = helper.GetObject('CashAccount',
        str(request[u'CashAccountNo'])).CastToLowestDescendant()
    if oCashAccount.isnull:
        raise 'Cash/Bank', 'Rekening %s tidak ditemukan' % request[u'CashAccountNo']        
  
    oItemCA = oTran.CreateAccountTransactionItem(oCashAccount)
    oItemCA.SetMutation('D', aAmount, 1.0)    
    oItemCA.Description = request[u'Description']
    oItemCA.SetJournalParameter('10')

    # Product Account
    oProduct = oFAAccount.LProductAccount
    #oProduct = helper.GetObject('ProductAccount',str(ProductAccountNo).CastToLowestDescendant()
    
    oItemPA = oTran.CreateAccountTransactionItem(oProduct)
    oItemPA.SetMutation('C',oFAAccount.NilaiSisa,1.0)
    oItemPA.Description = request[u'Description']
    oItemPA.SetJournalParameter('DA09')
    oItemPA.SetCollectionEntity(2)
    
    oTran.GenerateTransactionNumber('000')
    oTran.SaveInbox(params)
    FileKwitansi = oTran.GetKwitansi()
        
    # Check for auto approval
    corporate = helper.CreateObject('Corporate')
    if corporate.CheckLimitOtorisasi(request[u'Amount']):
      oTran.AutoApproval()

    config.Commit()
  except:
    config.Rollback()
    raise

  status,msg = oTran.CreateJournal()
  return GenerateResponse(status,msg,oTran.TransactionNo,FileKwitansi)
