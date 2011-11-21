import com.ihsan.foundation.pobjecthelper as phelper
import sys
import com.ihsan.util.customidgenAPI as customidgenAPI

def FormOnSetDataEx(uideflist,parameters):
  config = uideflist.config

  if parameters.DatasetCount == 0 :
#    rec = uideflist.uipInvoice.Dataset.AddRecord()
#    rec.Inputer = str(config.SecurityContext.UserId)
#    rec.BranchCode = config.SecurityContext.GetUserInfo()[4]
    
    return 1
  
  param = parameters.FirstRecord
  helper = phelper.PObjectHelper(config)

  BranchCode = config.SecurityContext.GetUserInfo()[4]
  ShowMode = param.ShowMode
  InvoiceId = param.InvoiceId
  
  if uideflist.uipInvoice.Dataset.RecordCount > 0 :
    recInvoice = uideflist.uipInvoice.Dataset.GetRecord(0)
  else:
    recInvoice = uideflist.uipInvoice.Dataset.AddRecord()
  # end if

  recInvoice.ShowMode = ShowMode
  recInvoice.Inputer = str(config.SecurityContext.UserId)
  recInvoice.BranchCode = BranchCode
  if ShowMode == 1:
    recInvoice.InvoiceNo = GenerateInvoiceNo(config,helper)
    oDefaultData = helper.GetObject('InvoiceProductDefaultData',BranchCode)
    if not oDefaultData.isnull :
      recInvoice.BankName = oDefaultData.InvoiceBankName
      recInvoice.BankAccount = oDefaultData.InvoiceBankAccountNumber
      recInvoice.BankAccountName = oDefaultData.InvoiceBankAccountName
      recInvoice.SignName = oDefaultData.InvoiceOfficerName
      recInvoice.JobPosition = oDefaultData.InvoiceOfficerPosition
      recInvoice.ContactPerson = oDefaultData.InvoiceContactPerson
      recInvoice.ContactPhone = oDefaultData.InvoiceContactPhone
    # end if not oDefaultData.isnull
  else:
    oInvoice = helper.GetObject('InvoiceProduct',InvoiceId)
    if oInvoice.TransactionId in [0,'',None] :
      raise 'PERINGATAN','Data Jurnal Transaksi Invoice Tidak Ditemukan'
    recInvoice.SetFieldByName('LBatch.BatchId',oInvoice.LTransaction.BatchId)
    recInvoice.SetFieldByName('LBatch.BatchNo',oInvoice.LTransaction.LBatch.BatchNo)
    recInvoice.InvoiceId = oInvoice.InvoiceId
    recInvoice.InvoiceNo = oInvoice.InvoiceNo
    recInvoice.InvoiceDate = oInvoice.GetAsTDateTime('InvoiceDate')
    recInvoice.TermDate = oInvoice.GetAsTDateTime('InvoiceTermDate')
    recInvoice.SponsorId = oInvoice.SponsorId
    recInvoice.SponsorName = oInvoice.LSponsor.full_name
    recInvoice.SponsorAddress = oInvoice.LSponsor.address
    recInvoice.ProgramName = oInvoice.LProductAccount.AccountName
    recInvoice.Amount = oInvoice.InvoiceAmount
    recInvoice.Description = oInvoice.Description
    recInvoice.BankName = oInvoice.InvoiceBankName
    recInvoice.BankAccount = oInvoice.InvoiceBankAccountNumber
    recInvoice.BankAccountName = oInvoice.InvoiceBankAccountName
    recInvoice.SignName = oInvoice.InvoiceOfficername
    recInvoice.JobPosition = oInvoice.InvoiceOfficerPosition
    recInvoice.ProductAccountNo = oInvoice.ProductAccountNo
    recInvoice.ContactPerson = oInvoice.InvoiceContactPerson
    recInvoice.ContactPhone = oInvoice.InvoiceContactPhone
  # end if else
  
def GenerateInvoiceNo(config,helper):
  RomanDigit = {
    1 : 'I', 2 : 'II', 3 : 'III', 4 : 'IV',
    5 : 'V', 6 : 'VI', 7 : 'VII', 8 : 'VIII',
    9 : 'IX', 10 : 'X', 11 : 'XI', 12 : 'XII',
  }
  
  # Prepare Code
  BranchCode = config.SecurityContext.GetUserInfo()[4]
  oBranch = helper.GetObject('Branch',BranchCode)
  ShortCode = oBranch.ShortCode
  Year,Month = config.ModLibUtils.DecodeDate(config.Now())[:2]
  
  # Generate sequence code
  config.BeginTransaction()
  try:
    customid = customidgenAPI.custom_idgen(config)
    IdCode = '%s-%s' % (ShortCode,Year)
    customid.PrepareGetID('INVOICE', IdCode)
    try:
      id = customid.GetLastID()
      SequenceNo = str(id)
      customid.Commit()
    except:
      customid.Cancel()
      raise '', str(sys.exc_info()[1])

    config.Commit()
  except:
    config.Rollback()
    raise

  param = {
    'ShortCode' : ShortCode,
    'RomanDigit' : RomanDigit[Month],
    'SequenceNo' : SequenceNo,
    'Year' : str(Year),
  }
  return 'PKPU-%(ShortCode)s/%(RomanDigit)s.%(SequenceNo)s/E/%(Year)s'% param

def ProsesVoucherNew(config,parameters,returns):
  status = returns.CreateValues(
    ['Is_Err',0],
    ['Err_Message',''],
    ['StreamName',''],
    ['VoucherName',''],
    ['InvoiceId',0],
  )

  config.BeginTransaction()
  try:
    BranchCode = config.SecurityContext.GetUserInfo()[4]
    helper = phelper.PObjectHelper(config)

    param = parameters.FirstRecord

    # Create Invoice
    oInvoice = helper.CreatePObject('InvoiceProduct')

    # Create Transaction
    oBatch = helper.GetObject('TransactionBatch', param.GetFieldByName('LBatch.BatchId'))
    oTran = oBatch.NewTransaction('INVC')

    InvoiceStream, VoucherStream = ProsesVoucher(config, param, oBatch, oTran, oInvoice, returns)
    
    # Auto Approve
    oTran.AutoApproval()

    status.InvoiceId = oInvoice.InvoiceId
    

    status.StreamName = InvoiceStream
    status.VoucherName = VoucherStream

    config.Commit()
  except:
    config.Rollback()
    status.Is_Err = 1
    status.Err_Message = str(sys.exc_info()[1])

def ProsesVoucherUpdate(config,parameters,returns):
  status = returns.CreateValues(
    ['Is_Err',0],
    ['Err_Message',''],
    ['StreamName',''],
    ['VoucherName',''],
    ['InvoiceId',0],
  )

  config.BeginTransaction()
  try:
    BranchCode = config.SecurityContext.GetUserInfo()[4]
    helper = phelper.PObjectHelper(config)

    param = parameters.FirstRecord

    # Get Invoice
    oInvoice = helper.GetObject('InvoiceProduct',param.InvoiceId)

    # Get Transaction
    oBatch = helper.GetObject('TransactionBatch', param.GetFieldByName('LBatch.BatchId'))

    oTran = oInvoice.LTransaction
    oTran.CancelTransaction()
    oTran.BatchId = oBatch.BatchId

    InvoiceStream, VoucherStream = ProsesVoucher(config, param, oBatch, oTran, oInvoice, returns)
    
    # Auto Approve
    oTran.AutoApprovalUpdate()

    status.InvoiceId = oInvoice.InvoiceId


    status.StreamName = InvoiceStream
    status.VoucherName = VoucherStream

    config.Commit()
  except:
    config.Rollback()
    status.Is_Err = 1
    status.Err_Message = str(sys.exc_info()[1])
    
def ProsesVoucher(config, param, oBatch, oTran, oInvoice, returns):
  helper = phelper.PObjectHelper(config)
  
  aAmount = param.Amount
  BranchCode = config.SecurityContext.GetUserInfo()[4]

  # Proses Data Invoice
  # Simpan Data invoice
  oInvoice.InvoiceNo = param.InvoiceNo
  oInvoice.InvoiceDate = param.InvoiceDate
  oInvoice.InvoiceTermDate = param.TermDate
  oInvoice.InvoiceAmount = aAmount or 0.0
  oInvoice.InvoiceAddress = param.SponsorAddress
  oInvoice.InvoiceBankName = param.BankName
  oInvoice.InvoiceBankAccountNumber = param.BankAccount
  oInvoice.InvoiceBankAccountName = param.BankAccountName
  oInvoice.InvoiceOfficername = param.SignName
  oInvoice.InvoiceOfficerPosition = param.JobPosition
  oInvoice.ProductAccountNo = param.ProductAccountNo
  oInvoice.SponsorId = param.SponsorId
  oInvoice.BranchCode = BranchCode
  oInvoice.Description = param.Description
  oInvoice.InvoiceContactPerson  = param.ContactPerson
  oInvoice.InvoiceContactPhone = param.ContactPhone
  oInvoice.CurrencyCode = param.GetFieldByName('LCurrency.Currency_Code')
  
  # Save Invoice Defaut Info
  # Menyimpan informasi Tujuan Transfer, Contact Person , Penanda Tangan
  oDefaultData = helper.GetObject('InvoiceProductDefaultData',BranchCode)
  if oDefaultData.isnull :
    oDefaultData = helper.CreatePObject('InvoiceProductDefaultData')
    oDefaultData.BranchCode = BranchCode
  # end if

  oDefaultData.InvoiceContactPerson  = param.ContactPerson
  oDefaultData.InvoiceContactPhone = param.ContactPhone
  oDefaultData.InvoiceBankName = param.BankName
  oDefaultData.InvoiceBankAccountNumber = param.BankAccount
  oDefaultData.InvoiceBankAccountName = param.BankAccountName
  oDefaultData.InvoiceOfficername = param.SignName
  oDefaultData.InvoiceOfficerPosition = param.JobPosition

  # Proses Data Transaction
  oTran.Inputer     = config.SecurityContext.UserId
  oTran.BranchCode  = BranchCode
  oTran.ReferenceNo = param.InvoiceNo
  oTran.Description = 'INVOICE %s' % param.InvoiceNo
  oTran.Amount = aAmount
  oTran.CurrencyCode = param.GetFieldByName('LCurrency.Currency_Code')
  oTran.ActualDate = oBatch.GetAsTDateTime('BatchDate')

  oProductAccount = helper.GetObject('ProductAccount',str(param.ProductAccountNo))

  #AccountCode = oProductAccount.GetAccountInterface('PIUTANG')
  AccountCode = helper.GetObject('ParameterGlobal', 'GLIPROJAR').Get()
  aValuta = '000'
  oAccount = helper.GetObject('Account',AccountCode)

  oItemGL = oTran.CreateGLTransactionItem(AccountCode, aValuta)
  oItemGL.RefAccountName = oAccount.Account_Name
  oItemGL.SetMutation('D', param.Amount, 1.0)
  oItemGL.Description = 'INVOICE %s' % param.InvoiceNo
  oItemGL.SetJournalParameter('INV01')

  oTran.GenerateTransactionNumber('000')
  oInvoice.TransactionId = oTran.TransactionId
  
  #filename = GenerateInvoice(config,param)
  # Generate Invoice Data
  InvoiceData = oInvoice.GenerateInvoicePrintData()
  corporate = helper.CreateObject('Corporate')
  sBaseFileName = "printinvoice.rtf"
  sFileName = corporate.GetUserHomeDir() + "\\" + sBaseFileName
  oFile = open(sFileName,'w')
  try:
    oFile.write(InvoiceData)
  finally:
    oFile.close()

  sw = returns.AddStreamWrapper()
  sw.LoadFromFile(sFileName)
  sw.MIMEType = 'application/msword'
  sw.Name = 'Invoice'

  InvoiceStream = sw.Name

  # Generate Kwitansi
  voucherfile = oTran.GetKwitansi()
  sw = returns.AddStreamWrapper()
  sw.Name = 'Kwitansi'
  sw.LoadFromFile(voucherfile)
  #sw.MIMEType = config.AppObject.GetMIMETypeFromExtension(filename)
  sw.MIMEType = 'application/msword'

  VoucherStream = sw.Name

  return InvoiceStream , VoucherStream
