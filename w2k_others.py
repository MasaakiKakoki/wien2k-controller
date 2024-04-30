import datetime
import os
import subprocess

from WIEN2k_controller import BaseController
import send_email as se

class OtherOperations(BaseController):

    def __init__(self, case):
        super().__init__(case)
        os.chdir(self.case_path)

    def scf_parallel_test(self, numofparallels, dir_name):
        self.force_stop()

        self.parallel = numofparallels

        self.initialization()

        subprocess.run(["rm", "-f", "*.broyd*"])
        scf_start = datetime.datetime.now()
        self.scf(cconv=0)
        scf_stop = datetime.datetime.now()
        run_time = scf_stop - scf_start

        self.save_lapw(dir_name)
        self._save_parallel_result(run_time)

    def _save_parallel_result(self, run_time):
        text = f"{self.parallel} => {run_time}\n"
        with open("Parallel_results.txt", "a") as f:
            f.write(text)


if __name__ == "__main__":
    def run():
        case = "ohwada_Au"
        oo = OtherOperations(case)

        for parallel in range(1, 7):
            oo.scf_parallel_test(numofparallels=parallel, dir_name=f"saved_para{parallel}")


    run()
    # mail = se.EmailFromMac()
    # mail.info_panel()
    # mail.send(run())