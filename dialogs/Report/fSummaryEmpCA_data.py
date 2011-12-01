import com.ihsan.foundation.pobjecthelper as phelper
import sys

def FormSetDataEx(uideflist, parameter) :
  config = uideflist.Config
  rec = uideflist.uipData.Dataset.AddRecord()
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.BranchName = str(config.SecurityContext.GetUserInfo()[5])

  Now = config.Now()

  y = config.ModLibUtils.DecodeDate(Now)[0]
  rec.BeginDate = config.ModLibUtils.EncodeDate(y,1,1)
  rec.EndDate = int(Now)


def SummaryEmpCA(config,params,returns):
  status = returns.CreateValues(
     ['Is_Err',0],['Err_Message',''],
     ['PeriodStr',''],['BranchName',''],
     ['BeginDateStr',''],['EndDateStr',''],
     ['BeginBalance',0.0],
     ['TotalDebet',0.0],
     ['TotalCredit',0.0],
     ['EndBalance',0.0],
  )
  
  BranchCode = params.FirstRecord.BranchCode
  BeginDate = params.FirstRecord.BeginDate
  EndDate = params.FirstRecord.EndDate
  
  try:
    helper = phelper.PObjectHelper(config)
    
    corporate = helper.CreateObject('Corporate')
    CabangInfo = corporate.GetCabangInfo(BranchCode)

    status.BranchName = CabangInfo.Nama_Cabang
    status.BeginDateStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
    status.EndDateStr = config.FormatDateTime('dd-mm-yyyy',EndDate)
    if BeginDate == EndDate :
      status.PeriodStr = config.FormatDateTime('dd-mm-yyyy',BeginDate)
    else:
      status.PeriodStr = "%s s/d %s" % (
                   config.FormatDateTime('dd-mm-yyyy',BeginDate),
                   config.FormatDateTime('dd-mm-yyyy',EndDate)
                 )
    # end if
    
    dsSummary = returns.AddNewDatasetEx(
     'summary',
     ';'.join([
       'NomorKaryawan: string',
       'NamaKaryawan: string',
       'Debet: float',
       'Kredit: float',
       'TotalMutasi: float',
       'SaldoAwal: float',
       'SaldoAkhir: float',
       'CurrencyName: string'
     ])
    )

    
    strSQL = " \
              select b.employeeidnumber, a.accountno, a.accountname, a.currencycode, c.short_name, \
                 (select sum(d.Amount) \
                     from transaction.transaction c, \
                          transaction.transactionitem d, \
                          transaction.accounttransactionitem e \
                     where c.transactionid = d.transactionid and d.transactionitemid = e.transactionitemid \
                         and c.actualdate between '%(BEGINDATE)s' and '%(ENDDATE)s'  and e.accountno=a.accountno \
                         and d.mutationtype='D') as Debet, \
                 (select sum(d.Amount) \
                     from transaction.transaction c, \
                          transaction.transactionitem d, \
                          transaction.accounttransactionitem e \
                     where c.transactionid = d.transactionid and d.transactionitemid = e.transactionitemid \
                         and c.actualdate between '%(BEGINDATE)s' and '%(ENDDATE)s'  and e.accountno=a.accountno \
                         and d.mutationtype='C') as Kredit \
              from transaction.financialaccount a, transaction.accountreceivable b, transaction.currency c \
              where a.accountno = b.accountno \
                  and a.currencycode = c.currency_code \
                  and b.AccountReceivableType = 'C' \
                  and a.branchcode = '%(BRANCHCODE)s' \
                 order by  a.accountname \
                " % {
                  'BRANCHCODE' : BranchCode ,
                  'BEGINDATE' : config.FormatDateTime('yyyy-mm-dd',BeginDate),
                  'ENDDATE' : config.FormatDateTime('yyyy-mm-dd',EndDate)
               }

    res = config.CreateSQL(strSQL).RawResult

    while not res.Eof:
      recSum = dsSummary.AddRecord()
      #recSum.NomorKaryawan = res.AccountNo
      recSum.NomorKaryawan = str(res.EmployeeIdNumber)
      recSum.NamaKaryawan = res.AccountName
      recSum.CurrencyName = res.Short_Name
      recSum.Debet = res.Debet or 0.0
      recSum.Kredit = res.Kredit or 0.0
      recSum.TotalMutasi = (res.Debet or 0.0 ) - ( res.Kredit or 0.0)
      
      AccountR = helper.GetObject('AccountReceivable',res.AccountNo)
      SaldoAwal = AccountR.GetBalanceByDate(BeginDate)
      recSum.SaldoAwal = SaldoAwal
      recSum.SaldoAkhir = SaldoAwal + recSum.TotalMutasi
      
      status.BeginBalance += recSum.SaldoAwal
      status.TotalDebet += recSum.Debet
      status.TotalCredit += recSum.Kredit
      status.EndBalance += recSum.SaldoAkhir
      
      res.Next()
      
    # end while
  except:
    status.Is_Err = 1
    status.Err_Message = str(sys.exc_info()[1])
