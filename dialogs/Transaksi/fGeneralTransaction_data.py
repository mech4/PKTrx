import com.ihsan.foundation.pobjecthelper as phelper
import sys
import simplejson


def FormSetDataEx(uideflist, params) :
  config = uideflist.config
  helper = phelper.PObjectHelper(uideflist.config)

  if params.GetDatasetByName('trparam') != None :
    oForm = helper.CreateObject('FormTransaksi')
    return oForm.SetDataEx(uideflist,params)

  Now = int(config.Now())
  rec = uideflist.uipTransaction.Dataset.AddRecord()
  rec.Inputer = str(config.SecurityContext.UserId)
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.TransactionDate = Now
  rec.ActualDate = Now
  rec.FloatTransactionDate = Now
  rec.TotalDebit = 0.0
  rec.TotalCredit = 0.0

  # Set Transaction Number
  #oService = helper.LoadScript('Transaction.TransactionHelper')
  rec.TransactionNo = '<AUTOGENERATED>' #oService.GetTransactionNumber(config)

def GetCurrencyRate(config, params, returns):
  app = config.AppObject
  param = params.FirstRecord
  res = app.rexecscript('accounting','appinterface/Currency.GetCurrencyInfo',
        app.CreateValues(['kode_valuta',param.CurrencyCode]))


  rec = res.FirstRecord
  if rec.Is_Error : raise '',rec.Err_Message
  returns.CreateValues(
    ['Full_Name',rec.Full_Name],
    ['Kurs_Tengah_BI',rec.Kurs_Tengah_BI],
  )

def SimpanData(config, params, returns):
  IsErr = 0
  ErrMessage = ''
  TransactionNo = ''
  helper = phelper.PObjectHelper(config)
  try :
    oTransaction = params.uipTransaction.GetRecord(0)

    request = {}
    request['ReferenceNo'] = oTransaction.ReferenceNo
    request['Description'] = oTransaction.Description
    request['TotalDebit'] = oTransaction.TotalDebit
    request['TotalCredit'] = oTransaction.TotalCredit
    request['Amount'] = oTransaction.TotalDebit
    request['Rate'] = 1.0
    request['Inputer'] = oTransaction.Inputer
    #request['BatchId'] = oTransaction.GetFieldByName('LBatch.BatchId')
    request['BranchCode'] = config.SecurityContext.GetUserInfo()[4]
    request['ActualDate'] = oTransaction.ActualDate
    request['TransactionNo'] = oTransaction.TransactionNo

    items = []

    for i in range(params.uipTransactionItem.RecordCount):
      oItem = params.uipTransactionItem.GetRecord(i)
      item = {}
      itemType = oItem.ItemType
      item['ItemType'] = itemType

      if itemType == 'C':
        item['DonorId'] = int(oItem.DonorId)
        item['DonorName'] = oItem.DonorName
        item['ProductId'] = oItem.ProductIdColl
        item['AccountNo'] = oItem.AccountNoColl
#        item['SponsorId'] = oItem.GetFieldByName('SponsorCol.SponsorId')
        item['VolunteerId'] = oItem.GetFieldByName('LVolunteer.VolunteerId')
        item['FundEntity'] = oItem.FundEntityCollection
      elif itemType == 'D':
        item['ProductId'] = oItem.ProductIdDist #oItem.GetFieldByName('ProductDist.ProductId')
        item['AccountNo'] = oItem.AccountNoDist
#        item['SponsorId'] = oItem.GetFieldByName('SponsorCol.SponsorId')
        item['SponsorId'] = oItem.SponsorId or 0
        item['SponsorName'] = oItem.SponsorName
        item['FundEntity'] = oItem.FundEntityDist
        item['Ashnaf'] = oItem.Ashnaf
        #item['DistItemAccount'] = oItem.GetFieldByName('LDistItem.Account_Code')
      elif itemType == 'B':
        item['AccountNo'] = oItem.GetFieldByName('LCashAccount.AccountNo')
      elif itemType == 'G':
        item['AccountCode'] = oItem.GetFieldByName('LLedger.Account_Code')
        item['AccountName'] = oItem.AccountName

      item['Valuta'] = oItem.CurrencyCode
      item['MutationType'] = oItem.MutationType
      item['Amount'] = oItem.Amount
      item['Rate']   = oItem.Rate
      item['Ekuivalen'] = oItem.Ekuivalen
      item['Description'] = oItem.Description

      items.append(item)
    #-- for

    request['Items']= items
    sRequest = simplejson.dumps(request)


    oService = helper.LoadScript('Transaction.GeneralTransaction')

    TransactionCode = 'GT'
    if oTransaction.ShowMode == 1:
      response = oService.CreateTransaction(TransactionCode, config, sRequest, params)
    else:
      response = oService.UpdateTransaction(TransactionCode, config, sRequest, params)


    response = simplejson.loads(response)
    TransactionNo = response[u'TransactionNo']

    filename = response[u'FileKwitansi'] # oTran.GetKwitansi()
    sw = returns.AddStreamWrapper()
    sw.Name = 'Kwitansi'
    sw.LoadFromFile(filename)
    #sw.MIMEType = config.AppObject.GetMIMETypeFromExtension(filename)
    sw.MIMEType = 'application/msword'

    StreamName = sw.Name

    IsErr = response[u'Status']
    ErrMessage = response[u'ErrMessage']

  except :
    IsErr = 1
    ErrMessage = str(sys.exc_info()[1])

  returns.CreateValues(
    ['IsErr', IsErr],
    ['ErrMessage', ErrMessage],
    ['TransactionNo',TransactionNo],
    )

